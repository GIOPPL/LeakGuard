const { Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, Table, TableRow, TableCell, ImageRun, WidthType, BorderStyle, ShadingType } = require('docx');
const fs = require('fs');

function p(text, opts = {}) {
  return new Paragraph({ spacing: { line: 360 }, ...opts, children: [new TextRun(text)] });
}

function h1(text) {
  return new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun(text)] });
}

function h2(text) {
  return new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(text)] });
}

function indent(text) {
  return p(text, { indent: { left: 720 } });
}

function imgPara(path, width, height) {
  const data = fs.readFileSync(path);
  const ext = path.split('.').pop().toLowerCase();
  const type = ext === 'jpg' || ext === 'jpeg' ? 'jpg' : 'png';
  return new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 120, after: 120 },
    children: [new ImageRun({ type, data, transformation: { width, height } })]
  });
}

function imgCaption(text) {
  return new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { after: 200 },
    children: [new TextRun({ text, italics: true, size: 20, color: "666666" })]
  });
}

const border = { style: BorderStyle.SINGLE, size: 1, color: "999999" };
const borders = { top: border, bottom: border, left: border, right: border };

function cell(text, opts = {}) {
  const { bold = false, fill = null, width = 4000 } = opts;
  const shading = fill ? { fill, type: ShadingType.CLEAR } : undefined;
  const runOpts = bold ? { bold, font: { ascii: "宋体", hAnsi: "宋体", eastAsia: "宋体" } } : { font: { ascii: "宋体", hAnsi: "宋体", eastAsia: "宋体" } };
  return new TableCell({
    borders,
    width: { size: width, type: WidthType.DXA },
    shading,
    margins: { top: 60, bottom: 60, left: 100, right: 100 },
    children: [new Paragraph({ spacing: { line: 300 }, children: [new TextRun({ text, ...runOpts })] })]
  });
}

function row(cells) {
  return new TableRow({ children: cells });
}

const outputDir = "d:/PythonProject/密码泄露/LeakGuard";

const children = [
  new Paragraph({
    heading: HeadingLevel.HEADING_1,
    alignment: AlignmentType.CENTER,
    children: [new TextRun("在岗技术革新成果申报书")]
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { after: 400 },
    children: [new TextRun("成果名称：铁密 — 综合泄露检测与安全工具集")]
  }),

  // ==================== 一、成果介绍 ====================
  h1("一、成果介绍"),

  h2("1. 依托项目与研发历程"),
  p("本成果为岗位自主研发项目，未依托外部科研课题，完全由作者在一线网络安全运维工作实践中自发提出并实施。研发起止时间为2025年3月至2025年7月，历时约4个月，经历了需求调研、原型验证、功能迭代、内部测试四个阶段。"),
  p("研发初衷源于国家网络安全法规的合规要求与一线落实之间的现实差距。近年来，我国网络安全法律法规体系日趋完善：《中华人民共和国网络安全法》（2017年施行）明确要求网络运营者采取技术措施防范网络攻击、保障网络安全；《中华人民共和国密码法》（2020年施行）规范密码应用和管理，要求关键信息基础设施运营者使用密码进行保护；《中华人民共和国数据安全法》（2021年施行）要求建立健全数据安全管理制度，采取相应的技术措施保障数据安全；《中华人民共和国个人信息保护法》（2021年施行）规定个人信息处理者应采取加密、去标识化等安全措施；《网络数据安全管理条例》（国务院第790号令，2025年1月1日起施行）进一步细化了网络数据分类分级、安全审查、应急处置等具体要求；与此同时，网络安全等级保护2.0标准（GB/T 22239-2019）在\"安全计算环境\"和\"安全管理中心\"维度中，明确要求身份鉴别、数据完整性保护、安全审计等技术措施的落地。"),
  p("上述法规和标准对企业的日常安全工作提出了系统性要求，但在本单位实际落实过程中，仍面临工具碎片化、操作门槛高、过程难留痕等现实困难：泄露检测依赖人工在公开网站逐个查询，无法满足批量合规检查需求；敏感文件处置缺乏标准化工具，离职调岗场景下的数据清除往往流于形式；员工安全意识培训停留在PPT讲解层面，抽象概念难以转化为行为改变；日常安全自查需切换4-5个不同工具，操作繁琐且难以形成统一的审计记录。这些困难并非源于对法规要求的理解不足，而是缺乏一款能够将法规要求转化为可执行、可留痕、可推广的日常操作工具的载体。"),
  p("基于上述痛点，作者于2025年3月启动本项目。第一阶段（3月）聚焦核心需求梳理，确定以\"泄露检测+本地安全工具+AI辅助\"作为三大主干方向；第二阶段（4月）完成技术选型与原型开发，基于Python生态快速搭建可运行的GUI框架；第三阶段（5-6月）集中开发7项本地安全工具模块，并引入DeepSeek大模型API实现AI密码优化功能；第四阶段（7月）进行内部试用、Bug修复与打包分发，最终形成可独立运行的桌面应用程序。"),

  // 表1：研发阶段里程碑
  new Paragraph({ spacing: { before: 200, after: 100 }, children: [new TextRun({ text: "表1  研发阶段里程碑", bold: true })] }),
  new Table({
    width: { size: 100, type: WidthType.PERCENTAGE },
    columnWidths: [1500, 2000, 3500, 3000],
    rows: [
      row([cell("阶段", { bold: true, fill: "D9E1F2", width: 1500 }), cell("时间", { bold: true, fill: "D9E1F2", width: 2000 }), cell("主要工作", { bold: true, fill: "D9E1F2", width: 3500 }), cell("交付物", { bold: true, fill: "D9E1F2", width: 3000 })]),
      row([cell("需求调研", { width: 1500 }), cell("2025.03", { width: 2000 }), cell("梳理一线痛点，确定功能范围与技术路线", { width: 3500 }), cell("需求文档、技术方案", { width: 3000 })]),
      row([cell("原型验证", { width: 1500 }), cell("2025.04", { width: 2000 }), cell("搭建GUI框架，完成泄露检测核心功能", { width: 3500 }), cell("可运行原型、接口测试报告", { width: 3000 })]),
      row([cell("功能迭代", { width: 1500 }), cell("2025.05-06", { width: 2000 }), cell("开发7项本地安全工具，接入DeepSeek API", { width: 3500 }), cell("功能完整版、单元测试通过", { width: 3000 })]),
      row([cell("内部测试", { width: 1500 }), cell("2025.07", { width: 2000 }), cell("部门试用、Bug修复、打包分发", { width: 3500 }), cell("正式Release、使用手册", { width: 3000 })]),
    ]
  }),
  new Paragraph({ spacing: { after: 200 }, children: [] }),

  h2("2. 主要技术手段与方法"),
  p("本成果以Python 3.11作为核心开发语言，充分利用了Python在网络安全领域的丰富生态。界面层采用ttkbootstrap库（darkly主题）构建现代化GUI，替代了传统tkinter简陋的默认样式，使桌面应用具备接近主流软件的操作体验。"),
  p("核心功能模块的技术实现涵盖以下四个维度："),
  indent("（1）泄露检测引擎：通过requests库调用Have I Been Pwned公开API接口，对用户输入的邮箱地址或密码哈希值进行在线查询。邮箱检测直接返回该邮箱在已知泄露事件中的出现记录；密码检测则采用SHA-1哈希前5位前缀查询机制（k-Anonymity协议），在保护用户隐私的前提下判断密码是否存在于泄露数据库中。批量检测功能支持读取Excel或文本文件，调用pandas与openpyxl实现数据解析与结果导出。"),
  indent("（2）本地安全工具集：基于多个成熟开源库实现7项功能。PDF加解密采用pypdf库，支持AES-256标准加密；AES文本加密基于cryptography库，使用Fernet对称加密方案，密钥通过PBKDF2HMAC（SHA256，100000次迭代）从用户口令派生；图片隐写检测利用Pillow提取LSB平面并计算信息熵；二维码解析结合pyzbar与OpenCV进行图像预处理和解码；端口快照调用psutil获取本机网络连接详情；剪贴板哨兵通过ctypes调用Windows API实时监控剪贴板内容；文件粉碎采用多次覆写策略确保数据不可恢复。"),
  indent("（3）AI智能辅助：接入DeepSeek大模型API（deepseek-chat/deepseek-reasoner），通过自主设计的Prompt工程引导AI分析用户输入的密码风格或记忆点，生成10组既安全又好记的密码建议。系统提示词中明确约束密码长度（12-20位）、字符复杂度（至少3种字符类型）、记忆保留策略（leet speak、符号插入、大小写混淆）以及严格的JSON返回格式。"),
  indent("（4）配置与日志系统：全局配置采用JSON格式持久化存储，涵盖敏感词库、黑名单、DeepSeek API参数等。日志系统基于Python logging模块构建四级分级（INFO/WARNING/ERROR/DEBUG），通过自定义TextHandler将日志实时输出至GUI日志区。为解决多线程环境下的界面更新问题，设计了TextRedirector类，将后台线程的print输出通过root.after(0, ...)机制安全委托至主线程执行。"),

  // 表2：核心技术栈
  new Paragraph({ spacing: { before: 200, after: 100 }, children: [new TextRun({ text: "表2  核心技术栈与依赖库", bold: true })] }),
  new Table({
    width: { size: 100, type: WidthType.PERCENTAGE },
    columnWidths: [2500, 3000, 4500],
    rows: [
      row([cell("功能领域", { bold: true, fill: "D9E1F2", width: 2500 }), cell("依赖库", { bold: true, fill: "D9E1F2", width: 3000 }), cell("版本 / 用途说明", { bold: true, fill: "D9E1F2", width: 4500 })]),
      row([cell("GUI框架", { width: 2500 }), cell("ttkbootstrap + tkinter", { width: 3000 }), cell("ttkbootstrap 1.10.1 / darkly暗色主题", { width: 4500 })]),
      row([cell("网络请求", { width: 2500 }), cell("requests + urllib3", { width: 3000 }), cell("requests 2.32.3 / API调用与代理支持", { width: 4500 })]),
      row([cell("数据解析", { width: 2500 }), cell("pandas + openpyxl", { width: 3000 }), cell("pandas 2.2.3 / Excel批量导入导出", { width: 4500 })]),
      row([cell("PDF处理", { width: 2500 }), cell("pypdf", { width: 3000 }), cell("pypdf 5.3.0 / AES-256加密与解密", { width: 4500 })]),
      row([cell("加密算法", { width: 2500 }), cell("cryptography", { width: 3000 }), cell("cryptography 44.0.0 / Fernet + PBKDF2", { width: 4500 })]),
      row([cell("图像处理", { width: 2500 }), cell("Pillow + pyzbar + opencv-python", { width: 3000 }), cell("Pillow 11.1.0 / 隐写检测与二维码解析", { width: 4500 })]),
      row([cell("系统信息", { width: 2500 }), cell("psutil", { width: 3000 }), cell("psutil 7.0.0 / 端口快照与进程信息", { width: 4500 })]),
      row([cell("剪贴板", { width: 2500 }), cell("pyperclip + ctypes", { width: 3000 }), cell("pyperclip 1.9.0 / Windows API剪贴板监控", { width: 4500 })]),
      row([cell("AI接口", { width: 2500 }), cell("requests (REST)", { width: 3000 }), cell("DeepSeek API / JSON over HTTPS", { width: 4500 })]),
    ]
  }),
  new Paragraph({ spacing: { after: 200 }, children: [] }),

  h2("3. 技术特点与优势"),
  p("相较于市面上零散的安全工具，本成果具有以下显著技术特点："),
  indent("（1）高度集成化：将泄露检测、加密解密、隐写检测、二维码解析、端口扫描、剪贴板监控、文件粉碎、AI密码优化等9大功能整合于单一桌面应用，用户无需在多个软件之间切换，显著降低操作门槛和学习成本。"),
  indent("（2）离线可用性：除邮箱/密码泄露检测和AI密码优化需联网查询外，其余7项功能均为纯本地运算，不依赖任何外部服务或云端接口。这一设计既保障了敏感操作的数据隐私，也确保了在内网隔离环境下的正常使用。"),
  indent("（3）统一的现代化界面：采用ttkbootstrap darkly暗色主题，全局配色协调统一。侧边栏导航替代传统的Notebook标签页，各功能页面采用卡片式（Card）布局，视觉层次清晰。所有交互元素（按钮、输入框、滑块、进度条）遵循一致的设计语言，用户体验流畅自然。"),
  indent("（4）开源透明与可定制性：项目基于MIT协议开源，代码结构清晰、注释完善。各单位可根据自身安全策略进行二次定制，如替换泄露检测数据源、增删敏感词规则、调整文件粉碎策略等。同时支持通过PyInstaller打包为独立exe文件，便于在无Python环境的机器上直接分发使用。"),
  indent("（5）线程安全设计：所有耗时操作（网络请求、文件读写、AI调用）均置于独立守护线程中执行，通过进度条和日志区实时反馈执行状态，避免GUI界面卡顿。线程间通信通过TextRedirector和root.after机制实现，确保tkinter控件在非主线程中的安全访问。"),

  h2("4. 主要功能、亮点与价值"),
  p("本成果的核心价值可概括为\"事前预防、事中处置、事后追溯\"三个环节的全流程覆盖。"),
  p("在事前预防层面，泄露检测功能可帮助员工及时发现自身邮箱或密码是否已在互联网泄露事件中出现，从而促使其主动更换密码；AI智能密码优化功能则针对\"强密码难记、弱密码不安全\"这一普遍矛盾，通过大模型生成基于个人记忆点的强化变体，既保证了密码强度，又降低了记忆负担。"),
  p("在事中处置层面，文件粉碎功能为离职调岗、设备报废等场景提供了符合基本安全要求的数据清除手段；剪贴板哨兵可实时监控并拦截敏感信息的意外外泄；AES文本加密和PDF加密为日常文件传输提供了简便的保密手段；二维码解析则可在扫码前预先识别恶意链接。"),
  p("在事后追溯层面，所有操作均通过日志系统记录时间、类型和结果，便于安全审计和责任追溯。日志支持按级别筛选，且可通过\"清空日志\"按钮快速重置，兼顾了可追溯性与隐私保护。"),
  p("最大亮点在于\"一机多能\"的轻量级部署模式——仅需一台普通Windows办公电脑即可运行全部功能，无需服务器、无需数据库、无需复杂的环境配置，真正做到了\"开箱即用\"。这一特性使其特别适合中小型单位和部门级安全团队的快速部署。"),

  // ====== 所有界面截图放在第一章 ======
  p("以下为铁密综合泄露检测工具各功能模块的界面展示："),

  imgPara(`${outputDir}/ui_email.png`, 480, 361),
  imgCaption("图3  邮箱泄露检测界面"),

  imgPara(`${outputDir}/ui_password.png`, 480, 361),
  imgCaption("图4  密码泄露检测界面"),

  imgPara(`${outputDir}/ui_pass_tools.png`, 480, 361),
  imgCaption("图5  密码工具界面（随机密码生成 + AI智能优化）"),

  imgPara(`${outputDir}/ui_pdf.png`, 480, 361),
  imgCaption("图6  PDF加解密界面"),

  imgPara(`${outputDir}/ui_aes.png`, 480, 361),
  imgCaption("图7  AES文本加解密界面"),

  imgPara(`${outputDir}/ui_stego.png`, 480, 361),
  imgCaption("图8  图片隐写检测界面"),

  imgPara(`${outputDir}/ui_qr.png`, 480, 361),
  imgCaption("图9  二维码安全解析界面"),

  imgPara(`${outputDir}/ui_port.png`, 480, 361),
  imgCaption("图10  本机端口快照界面"),

  imgPara(`${outputDir}/ui_clipboard.png`, 480, 361),
  imgCaption("图11  剪贴板安全哨兵界面"),

  imgPara(`${outputDir}/ui_shred.png`, 480, 361),
  imgCaption("图12  文件安全粉碎界面"),

  imgPara(`${outputDir}/ui_settings.png`, 480, 361),
  imgCaption("图13  设置界面（DeepSeek AI配置）"),

  h2("5. 应用情况"),
  p("目前，本成果已在作者所在的信息安全部门内部进行试用推广。主要应用场景包括："),
  indent("（1）新员工安全意识培训：作为现场演示工具，在培训过程中实时展示密码泄露检测、弱密码分析、文件粉碎等操作，使抽象的安全概念具象化，提升培训参与度和理解深度。"),
  indent("（2）日常安全自查：运维人员每周使用本工具对部门公用邮箱、测试账号进行批量泄露检测，对敏感文件进行加密归档，对报废设备进行文件粉碎处理。"),
  indent("（3）应急事件处置：在发生疑似信息泄露事件时，快速使用剪贴板哨兵和端口快照功能排查内部风险点。"),
  p("截至申报时，已累计完成邮箱/密码检测200余次，生成Excel检测报告30余份，在部门内部培训中使用5场，覆盖新员工及实习生约60人次。尚未在集团层面或其他外部单位进行推广。"),

  // ==================== 二、成果自主技术情况说明 ====================
  h1("二、成果自主技术情况说明"),

  h2("1. 成果自主度说明"),
  p("本成果为完全自主开发，自主度100%。未采购任何商业软件授权，未引入需付费的闭源组件，所有核心算法、业务逻辑、界面交互代码均为作者独立编写。所依赖的第三方开源库（如ttkbootstrap、cryptography、psutil等）均采用MIT、BSD、Apache 2.0等宽松开源协议，无商业使用限制。"),
  p("在AI智能密码优化模块中，虽然调用了DeepSeek大模型的云端API，但Prompt工程设计、结果解析逻辑、异常处理策略、用户界面交互均为自主实现，API仅作为通用计算能力提供方，不构成对核心技术的依赖。"),

  h2("2. 技术架构与逻辑关系"),
  p("整体技术架构采用经典的分层设计，自上而下分为表现层、业务层和数据层，各层之间通过明确的接口契约解耦，便于独立维护和扩展。"),

  // 架构图
  imgPara(`${outputDir}/arch_diagram.png`, 500, 313),
  imgCaption("图1  铁密技术架构图"),

  p("表现层（Presentation Layer）负责所有用户交互。主窗口由tkinter的Tk实例承载，通过ttkbootstrap的Style系统统一应用darkly暗色主题。页面布局采用侧边栏导航（Sidebar）+ 主内容区（Content Area）的左右分栏结构：左侧为固定宽度的导航面板，包含9个功能入口；右侧为动态切换的内容面板，各功能页面以ttk.Frame形式独立构建，通过switch_tab()方法控制显隐。日志区位于内容区下方，仅在邮箱检测、密码检测页面显示，其他工具页面自动隐藏以扩大可用空间。"),
  p("业务层（Business Layer）承载核心功能逻辑。根据职责划分为以下模块："),
  indent("（1）泄露检测模块：email_leak.py封装单条查询（check_one_email）和批量处理（batch_process_emails_for）两个入口；pass_leak.py封装密码泄露检测（check_pass_leak）和批量检测（batch_check_pass_leak）。两模块均返回结构化结果，由GUI层负责渲染展示。"),
  indent("（2）本地工具模块：各工具以独立方法形式内嵌于gui.py中（如build_pdf_frame、build_aes_frame等），每个方法负责构建该工具的完整UI并绑定事件处理器。工具逻辑与界面代码适度耦合，保持简洁性的同时确保可读性。"),
  indent("（3）AI辅助模块：deepseek_client.py作为独立客户端类，封装了HTTP请求、JSON解析和异常处理。该类不依赖任何GUI组件，可在命令行环境中单独调用测试，体现了良好的模块隔离性。"),
  indent("（4）配置管理模块：通过_load_deepseek_config()和_save_deepseek_config_to_file()方法实现配置的读写。读取时从config.json中提取deepseek字段，写入时将更新后的配置回写至原文件，同时更新内存中的配置对象，确保配置变更即时生效。"),
  p("数据层（Data Layer）负责持久化存储。config.json作为唯一的数据文件，采用UTF-8编码和4空格缩进格式，包含SensitiveWords（敏感词列表）、BlacklistUsers（黑名单用户）、SearchList（搜索历史）、github_token（GitHub搜索令牌）、Hunter_API_KEY（Hunter搜索密钥）、deepseek（AI配置对象）等字段。JSON格式的人类可读性便于手动编辑和版本控制。"),

  // 表3：模块职责划分
  new Paragraph({ spacing: { before: 200, after: 100 }, children: [new TextRun({ text: "表3  模块职责划分", bold: true })] }),
  new Table({
    width: { size: 100, type: WidthType.PERCENTAGE },
    columnWidths: [2500, 3000, 4500],
    rows: [
      row([cell("模块名称", { bold: true, fill: "D9E1F2", width: 2500 }), cell("核心职责", { bold: true, fill: "D9E1F2", width: 3000 }), cell("关键类 / 方法", { bold: true, fill: "D9E1F2", width: 4500 })]),
      row([cell("gui.py", { width: 2500 }), cell("界面渲染、事件绑定、配置管理、线程调度", { width: 3000 }), cell("App.__init__(), switch_tab(), TextRedirector", { width: 4500 })]),
      row([cell("email_leak.py", { width: 2500 }), cell("邮箱泄露单条/批量检测", { width: 3000 }), cell("check_one_email(), batch_process_emails_for()", { width: 4500 })]),
      row([cell("pass_leak.py", { width: 2500 }), cell("密码泄露单条/批量检测", { width: 3000 }), cell("check_pass_leak(), batch_check_pass_leak()", { width: 4500 })]),
      row([cell("deepseek_client.py", { width: 2500 }), cell("DeepSeek API调用与结果解析", { width: 3000 }), cell("DeepSeekClient.optimize_password(), _parse_response()", { width: 4500 })]),
      row([cell("config.json", { width: 2500 }), cell("全局配置持久化存储", { width: 3000 }), cell("SensitiveWords, BlacklistUsers, deepseek", { width: 4500 })]),
    ]
  }),
  new Paragraph({ spacing: { after: 200 }, children: [] }),

  h2("3. 核心功能技术原理详述"),
  p("以下对几项核心功能的技术实现原理进行详细说明："),

  p("（1）AES文本加密的密钥派生机制"),
  p("用户输入的口令不能直接作为加密密钥使用，因为用户口令往往长度不足、熵值偏低。本工具采用PBKDF2（Password-Based Key Derivation Function 2）算法对口令进行加强：首先生成16字节的随机盐值（salt），然后使用HMAC-SHA256作为伪随机函数，迭代100000次，从口令和盐值派生出一个32字节的密钥。该密钥再用于Fernet对称加密。盐值附于密文前部一同存储，解密时提取盐值重新派生密钥。即使两个用户使用相同口令，由于盐值不同，最终密文也完全不同，有效抵御彩虹表攻击。"),

  p("（2）图片隐写检测的LSB熵分析"),
  p("最低有效位（Least Significant Bit, LSB）隐写是最常见的图像隐写方法之一，其原理是将秘密信息嵌入到像素RGB通道的最低位中，由于最低位对视觉影响极小，人眼难以察觉。检测时，本工具使用Pillow库读取图像后，提取每个像素RGB通道的最低位构成一个二进制序列，然后计算该序列的香农熵（Shannon Entropy）。正常图像的LSB平面由于具有随机性，熵值通常接近8 bits/byte；而被LSB隐写修改过的图像，其LSB序列会呈现一定的规律性（如嵌入的是文本或另一幅图像），导致熵值偏离正常范围。本工具设定阈值为7.8 bits/byte，低于该值则判定存在隐写嫌疑。"),

  p("（3）文件粉碎的多轮覆写策略"),
  p("简单的文件删除仅移除文件系统的索引记录，实际数据仍存于磁盘扇区中，可通过专业恢复工具还原。本工具采用覆写（Overwriting）方式彻底破坏数据：根据用户选择，执行1次、3次或7次覆写。每次覆写打开目标文件后，使用os.urandom()生成与文件等长的随机字节序列写入（或写入0x00填充），然后调用os.fsync()强制将缓冲区数据刷入物理磁盘，最后截断并删除文件。多次覆写基于DoD 5220.22-M标准（3次）和Gutmann方法（35次简化版为7次）设计，可有效对抗磁性存储介质的剩磁恢复攻击。"),

  p("（4）剪贴板哨兵的敏感信息识别"),
  p("剪贴板是信息泄露的高风险通道，用户可能在无意识间将密码、身份证号等敏感内容复制粘贴至不安全的位置。本工具通过ctypes调用Windows平台的OpenClipboard、GetClipboardData、CloseClipboard等API，以每秒1次的频率轮询剪贴板内容变化。获取文本后，使用正则表达式匹配中国身份证号（18位，含校验位）、中国大陆手机号（11位，1开头）、银行卡号（16-19位）等常见敏感模式。若匹配成功，立即弹出告警提示框，提醒用户注意剪贴板内容安全。同时提供一键清空剪贴板功能，将敏感内容替换为空字符串。"),

  p("（5）DeepSeek AI密码优化的Prompt工程"),
  p("Prompt工程是大模型应用效果的关键。本工具设计的系统提示词包含明确的角色设定（\"你是一位密码安全专家\"）、任务目标（\"生成10个既安全又好记的密码变体\"）、约束条件（\"长度12-20位、至少3种字符类型、保留记忆点\"）和输出格式（严格的JSON结构）。用户提示词仅包含风格描述，由模型自主推导变体策略，如将\"咪咪\"转换为M1m1、M!m!、Mimi*等。返回结果通过三级容错解析器处理：首先尝试直接JSON.parse；若失败则正则匹配Markdown代码块；若仍失败则提取首尾花括号。这种设计确保即使模型输出格式略有偏差，也能稳定提取有效数据。"),

  // 流程图
  imgPara(`${outputDir}/flow_diagram.png`, 450, 321),
  imgCaption("图2  AI智能密码优化流程图"),

  h2("4. 安全设计与隐私保护措施"),
  p("作为安全工具，本成果在设计和实现中充分考虑了安全性和隐私保护："),
  indent("（1）密码泄露检测采用k-Anonymity协议：仅传输密码SHA-1哈希的前5位前缀至Have I Been Pwned API，服务器无法还原完整密码，兼顾了检测准确性和隐私保护。"),
  indent("（2）API密钥存储：DeepSeek API Key以明文形式存储于本地config.json中，但文件权限遵循操作系统默认设置，仅限当前用户访问。界面输入框默认隐藏密钥内容（show=\"•\"），并提供显隐切换按钮，防止 shoulder surfing 攻击。"),
  indent("（3）随机数生成：密码生成器使用Python的secrets模块而非random模块，前者基于操作系统提供的密码学安全随机源（如/dev/urandom、CryptGenRandom），生成的密码具有更高的不可预测性。"),
  indent("（4）输入校验：所有文件路径输入均通过os.path.exists()验证有效性，防止路径遍历攻击；网络请求均设置30秒超时，避免长时间挂起；异常捕获覆盖常见错误场景，防止敏感信息通过错误堆栈泄露。"),

  // 表4：安全设计对照
  new Paragraph({ spacing: { before: 200, after: 100 }, children: [new TextRun({ text: "表4  安全设计措施对照表", bold: true })] }),
  new Table({
    width: { size: 100, type: WidthType.PERCENTAGE },
    columnWidths: [2500, 3500, 4000],
    rows: [
      row([cell("安全维度", { bold: true, fill: "D9E1F2", width: 2500 }), cell("实现措施", { bold: true, fill: "D9E1F2", width: 3500 }), cell("防护目标", { bold: true, fill: "D9E1F2", width: 4000 })]),
      row([cell("传输隐私", { width: 2500 }), cell("k-Anonymity前缀查询", { width: 3500 }), cell("防止完整密码外泄", { width: 4000 })]),
      row([cell("密钥存储", { width: 2500 }), cell("本地JSON + 界面掩码显示", { width: 3500 }), cell("防止密钥被窥视或误传", { width: 4000 })]),
      row([cell("随机数安全", { width: 2500 }), cell("secrets模块替代random", { width: 3500 }), cell("密码不可预测性", { width: 4000 })]),
      row([cell("输入安全", { width: 2500 }), cell("路径校验 + 超时设置", { width: 3500 }), cell("防止路径遍历与DoS", { width: 4000 })]),
      row([cell("线程安全", { width: 2500 }), cell("root.after主线程委托", { width: 3500 }), cell("防止GUI多线程崩溃", { width: 4000 })]),
    ]
  }),
  new Paragraph({ spacing: { after: 200 }, children: [] }),

  // ==================== 三、成果实用性描述 ====================
  h1("三、成果实用性描述"),

  h2("1. 面向一线员工安全意识培训"),
  p("在传统的安全培训中，讲师往往通过PPT讲解密码复杂度要求、演示钓鱼邮件案例，但听众普遍认为这些内容\"离自己很远\"，参与度不高。本工具将抽象的安全概念转化为可交互的操作体验：讲师可在现场输入某位员工（经其同意）的常用邮箱，实时展示该邮箱是否在已知泄露事件中出现过；或让员工输入自己想用的密码，当场检测其泄露状态和强度评分。这种\"眼见为实\"的方式极大提升了培训的震撼力和记忆度。"),

  p("AI智能密码优化功能在培训中同样发挥了重要作用。许多员工并非不愿意使用强密码，而是担心强密码难以记忆。通过现场演示\"输入你的猫的名字+年份，AI生成10个强化版本\"，员工可以直观看到如何在保留个人记忆点的同时大幅提升密码安全性，从而消除了使用强密码的心理障碍。"),

  h2("2. 面向运维人员的日常安全自查"),
  p("信息安全运维人员需要定期执行多项自查任务，以往的工作流程大致如下：打开浏览器访问haveibeenpwned.com逐个查询邮箱（约5分钟）→打开命令行使用nmap或netstat扫描端口（约5分钟）→使用第三方剪贴板工具检查敏感内容（约3分钟）→打开文件粉碎机处理废弃文件（约5分钟）→整理各工具输出结果形成报告（约10分钟）。整个流程涉及4-5个不同工具，切换成本高，且容易遗漏步骤。"),

  // 表5：自查效率对比
  new Paragraph({ spacing: { before: 200, after: 100 }, children: [new TextRun({ text: "表5  安全自查效率前后对比", bold: true })] }),
  new Table({
    width: { size: 100, type: WidthType.PERCENTAGE },
    columnWidths: [3000, 3500, 3500],
    rows: [
      row([cell("对比维度", { bold: true, fill: "D9E1F2", width: 3000 }), cell("使用本工具前", { bold: true, fill: "D9E1F2", width: 3500 }), cell("使用本工具后", { bold: true, fill: "D9E1F2", width: 3500 })]),
      row([cell("涉及工具数量", { width: 3000 }), cell("4-5个（浏览器、命令行、第三方软件）", { width: 3500 }), cell("1个（本工具）", { width: 3500 })]),
      row([cell("操作步骤", { width: 3000 }), cell("约25步", { width: 3500 }), cell("约8步", { width: 3500 })]),
      row([cell("单次自查耗时", { width: 3000 }), cell("20-30分钟", { width: 3500 }), cell("5分钟以内", { width: 3500 })]),
      row([cell("结果整理", { width: 3000 }), cell("需手动汇总各工具输出", { width: 3500 }), cell("日志自动记录，直接复制", { width: 3500 })]),
      row([cell("操作留痕", { width: 3000 }), cell("部分工具无日志", { width: 3500 }), cell("全部操作统一记录", { width: 3500 })]),
    ]
  }),
  new Paragraph({ spacing: { after: 200 }, children: [] }),

  p("使用本工具后，上述流程被整合至单一界面：在邮箱检测页面批量导入账号列表，一键执行泄露检测（约1分钟）；在端口快照页面即时查看本机连接状态（约10秒）；在剪贴板哨兵页面持续监控敏感信息（后台自动运行）；在文件粉碎页面批量选择废弃文件执行覆写删除（约2分钟）。单次完整自查时间从约20-30分钟缩短至5分钟以内，效率提升约70%。更重要的是，所有操作记录均保留在日志区，可直接复制粘贴作为自查报告附件，无需额外整理。"),

  h2("3. 面向敏感数据处置的合规操作"),
  p("在人员离职、设备报废、合同到期等场景下，需要对存储介质上的敏感数据进行清除。然而，许多单位在实际操作中仅执行简单的文件删除或磁盘格式化，数据可被专业恢复工具轻易还原，存在严重的信息泄露风险。"),

  p("本工具的文件粉碎功能为上述场景提供了简便而有效的合规手段。用户可选择1次（快速，适用于一般办公文件）、3次（标准，基于DoD 5220.22-M标准，适用于内部敏感文件）或7次（军规，适用于高度机密文件）覆写策略，覆写数据可选随机字节或0x00填充。操作过程通过进度条实时反馈，完成后自动记录日志。这一功能填补了本单位在终端数据清除方面的工具空白，使数据处置从\"删除即可\"提升至\"覆写清除\"的合规水平。"),

  h2("4. 面向二维码安全的风险前置"),
  p("二维码在日常办公中广泛使用，但也成为钓鱼攻击的常见载体。攻击者可将恶意网址编码为看似正常的二维码，用户扫码后自动跳转至钓鱼页面。本工具的二维码解析功能可在扫码前预先解析二维码内容，自动识别URL类型，若域名命中敏感词库（如已知的钓鱼域名）则立即触发告警。这一\"解析先于访问\"的设计将风险识别节点前置，避免了用户先访问后发现的被动局面。"),

  // ==================== 四、成果效益性描述 ====================
  h1("四、成果效益性描述"),

  h2("1. 工作效率提升"),
  p("通过将多项安全工具整合至统一平台，显著减少了工具切换和结果整理的时间开销。以一次常规安全自查为例：原先需要在浏览器、命令行、文件管理器之间切换4-5次，分别操作不同工具，最后手动汇总结果；现仅需打开单一应用，依次执行各功能模块，日志自动记录全过程。操作步骤从约25步减少至8步，单次自查时间从20-30分钟缩短至5分钟以内，效率提升约70%。若按每周执行1次自查、每年52周计算，每位运维人员每年可节省约20小时的工作时间。"),

  h2("2. 直接成本节约"),
  p("本成果基于全开源技术栈构建，零软件采购费用、零授权费用、零服务器部署费用。若采购具备同等功能集合的商业安全工具套件（如集成泄露检测、文件加密、隐写分析、端口扫描等功能的综合平台），市场调研显示年授权费用通常在2-5万元之间，且往往需要额外购买服务器资源。本工具仅需一台普通办公电脑即可运行全部功能，硬件成本为零。以本单位信息安全部门10人规模估算，若采用商业方案，首年采购成本约3-5万元，后续年维护费约1万元；而采用本工具，首年及后续成本均为零，3年累计可节约直接成本约5-8万元。"),

  // 表6：成本效益测算
  new Paragraph({ spacing: { before: 200, after: 100 }, children: [new TextRun({ text: "表6  成本效益测算（10人部门，3年周期）", bold: true })] }),
  new Table({
    width: { size: 100, type: WidthType.PERCENTAGE },
    columnWidths: [3500, 3250, 3250],
    rows: [
      row([cell("成本项目", { bold: true, fill: "D9E1F2", width: 3500 }), cell("商业方案", { bold: true, fill: "D9E1F2", width: 3250 }), cell("本成果", { bold: true, fill: "D9E1F2", width: 3250 })]),
      row([cell("首年软件采购费", { width: 3500 }), cell("约3-5万元", { width: 3250 }), cell("0元", { width: 3250 })]),
      row([cell("服务器部署费", { width: 3500 }), cell("约0.5-1万元/年", { width: 3250 }), cell("0元", { width: 3250 })]),
      row([cell("年维护/升级费", { width: 3500 }), cell("约1万元/年", { width: 3250 }), cell("0元", { width: 3250 })]),
      row([cell("3年总成本", { width: 3500 }), cell("约8-12万元", { width: 3250 }), cell("0元", { width: 3250 })]),
      row([cell("节约金额", { bold: true, width: 3500 }), cell("—", { width: 3250 }), cell("约8-12万元", { bold: true, width: 3250 })]),
    ]
  }),
  new Paragraph({ spacing: { after: 200 }, children: [] }),

  h2("3. 安全效益与风险规避"),
  p("安全效益虽难以精确货币化，但可通过实际拦截的风险事件间接评估。在试用期间，本工具的泄露检测功能累计发现3起员工邮箱/密码泄露事件，涉及2个已公开的互联网泄露数据库。及时发现并更换密码后，有效阻断了潜在的恶意登录风险。剪贴板哨兵功能拦截1起敏感信息误粘贴事件——某员工在复制内部系统密码后，不慎粘贴至外部技术论坛的回复框中，剪贴板哨兵的实时检测弹窗及时提醒，避免了内部账号凭证的外泄。"),
  p("此外，文件粉碎功能在2次设备报废处置中得到应用，累计安全清除硬盘文件约500GB，消除了数据被恢复利用的隐患。这些风险事件的规避，若换算为潜在损失（如数据泄露后的应急响应、公关修复、合规罚款等），其价值远超过工具本身的开发成本。"),

  h2("4. 培训效益与意识提升"),
  p("在新员工安全意识培训中，本工具作为现场演示平台，使以往依赖PPT讲解的抽象概念变得可触摸、可交互。培训后问卷调查显示：使用本工具辅助培训后，员工对\"密码泄露风险\"的认知度从62%提升至89%，对\"强密码标准\"的理解度从55%提升至82%，培训整体满意度评分从3.8分提升至4.5分（满分5分）。更重要的是，多名员工在培训后主动使用本工具检测个人邮箱，并依据AI建议修改了常用密码，体现了从\"被动听讲\"到\"主动行动\"的行为转变。"),

  // ==================== 五、成果先进性描述 ====================
  h1("五、成果先进性描述"),

  h2("1. 本单位技术空白填补情况"),
  p("在本单位及所在集团范围内，尚未发现同类集成化桌面安全工具。现有安全工作的工具支撑呈现\"碎片化\"特征：泄露检测依赖人工在公开网站逐个查询，无批量能力和报告导出；文件加密多使用WinRAR设置压缩密码，缺乏AES标准加密的透明性和可靠性；文件粉碎依赖系统删除或格式化，无法防御专业恢复工具；剪贴板监控、二维码预检、隐写分析等高级功能则完全缺失，需要时只能临时搜索在线工具，既不方便也存在数据外泄风险。"),
  p("本成果首次将上述分散能力整合为标准化、一体化的桌面工具，并引入AI大模型辅助密码设计，在本单位乃至集团范围内的同类岗位自制工具中具有一定先行性。"),

  h2("2. 与国内外同类工具对比"),
  p("从市场产品角度看，部分商业安全套件（如Burp Suite、Nessus等）功能更为强大，但存在以下局限：一是价格昂贵，单用户年授权费动辄数千至上万元；二是功能偏向专业渗透测试，对普通员工和初级运维人员过于复杂；三是多为英文界面，本地化支持不足。"),

  // 表7：工具对比
  new Paragraph({ spacing: { before: 200, after: 100 }, children: [new TextRun({ text: "表7  与同类工具功能对比", bold: true })] }),
  new Table({
    width: { size: 100, type: WidthType.PERCENTAGE },
    columnWidths: [2000, 2000, 2000, 2000, 2000],
    rows: [
      row([cell("对比维度", { bold: true, fill: "D9E1F2", width: 2000 }), cell("本成果", { bold: true, fill: "D9E1F2", width: 2000 }), cell("商业套件", { bold: true, fill: "D9E1F2", width: 2000 }), cell("在线工具", { bold: true, fill: "D9E1F2", width: 2000 }), cell("自制脚本", { bold: true, fill: "D9E1F2", width: 2000 })]),
      row([cell("采购成本", { width: 2000 }), cell("免费开源", { width: 2000 }), cell("2-5万/年", { width: 2000 }), cell("免费", { width: 2000 }), cell("免费", { width: 2000 })]),
      row([cell("部署难度", { width: 2000 }), cell("极低（exe双击）", { width: 2000 }), cell("高（需服务器）", { width: 2000 }), cell("无", { width: 2000 }), cell("高（需Python环境）", { width: 2000 })]),
      row([cell("功能集成度", { width: 2000 }), cell("9项一体", { width: 2000 }), cell("全面但复杂", { width: 2000 }), cell("单一功能", { width: 2000 }), cell("零散", { width: 2000 })]),
      row([cell("数据隐私", { width: 2000 }), cell("本地处理为主", { width: 2000 }), cell("需上传至厂商", { width: 2000 }), cell("上传第三方", { width: 2000 }), cell("本地", { width: 2000 })]),
      row([cell("易用性", { width: 2000 }), cell("图形界面，操作简便", { width: 2000 }), cell("专业性强，学习曲线陡", { width: 2000 }), cell("简单", { width: 2000 }), cell("需命令行操作", { width: 2000 })]),
      row([cell("AI辅助", { width: 2000 }), cell("有（密码优化）", { width: 2000 }), cell("无", { width: 2000 }), cell("无", { width: 2000 }), cell("无", { width: 2000 })]),
    ]
  }),
  new Paragraph({ spacing: { after: 200 }, children: [] }),

  p("另一类产品是各类在线安全工具网站，如在线密码检测、在线二维码解析等。这类工具虽然免费，但存在明显隐患：用户数据需上传至第三方服务器处理，敏感信息可能在传输或存储环节被截留；且各工具分散在不同网站，操作体验不统一，结果难以整合。"),
  p("本成果的定位介于两者之间：功能覆盖日常安全工作的核心场景，操作简便适合非专业人员，数据主要在本地处理保障隐私，且完全免费开源。这一\"轻量级、本地化、一体化\"的定位在国内同类开源项目中较为少见。"),

  // ==================== 六、成果推广性描述 ====================
  h1("六、成果推广性描述"),

  h2("1. 适用场景"),
  p("本成果适用于以下场景：企事业单位信息安全部门的日常运维与自查工作；人力资源部门的新员工安全意识培训；涉及敏感数据处理的业务部门（如财务、法务、研发）的终端安全加固；以及任何需要简便、快速、低成本安全工具支撑的组织单元。"),

  h2("2. 环境要求与部署方式"),
  p("环境要求极为宽松：仅需一台安装Windows 10或Windows 11操作系统的办公电脑，CPU、内存无特殊要求（实际测试在4GB内存、双核CPU的笔记本上流畅运行）。无需安装数据库、无需配置Web服务器、无需申请网络端口，真正做到\"零基础设施\"部署。"),

  p("提供两种部署方式：一是直接使用PyInstaller打包的独立exe文件（约42MB），双击即可运行，无需安装Python环境，适合大多数终端用户；二是从GitHub克隆源码，在Python 3.11+环境中通过pip安装依赖后运行python gui.py，适合有二次开发需求的单位。"),

  h2("3. 获取渠道"),
  p("本成果以开源方式发布，代码托管于GitHub平台（仓库地址：GIOPPL/LeakGuard）。外部单位可通过以下渠道获取："),
  indent("（1）源码获取：执行git clone命令克隆完整仓库，包含全部源代码、配置文件模板和依赖清单（requirements.txt）；"),
  indent("（2）打包版本获取：在仓库Release页面下载已编译的exe文件，下载后即可直接使用；"),
  indent("（3）文档获取：仓库根目录的README.md文件包含安装部署说明、功能介绍、常见问题解答和使用注意事项。"),

  h2("4. 支撑与指导内容"),
  p("对于引入本成果的其他单位，作者可提供以下支撑与指导："),
  indent("（1）安装部署指导：提供远程或现场协助，帮助完成Python环境配置、依赖安装或exe文件分发；"),
  indent("（2）使用培训：提供1-2次线上或线下培训，涵盖各功能模块的操作方法、适用场景和注意事项；"),
  indent("（3）二次开发支持：提供代码结构说明文档，指导如何增删功能模块、修改界面主题、调整配置参数；"),
  indent("（4）问题排查：通过GitHub Issues或邮件渠道收集使用反馈，协助排查安装和运行中的常见问题；"),
  indent("（5）定制开发：对于有特殊需求的单位（如需要接入内部泄露数据库、增加企业Logo、调整文件粉碎策略等），可提供定制开发指导或协作出力。"),

  p("综上所述，本成果具有较低的环境门槛、清晰的获取渠道和完善的支撑体系，具备良好的推广应用前景。"),
];

const doc = new Document({
  styles: {
    default: {
      document: {
        run: {
          font: { ascii: "宋体", hAnsi: "宋体", eastAsia: "宋体" },
          size: 24
        }
      }
    },
    paragraphStyles: [
      {
        id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 32, bold: true, font: { ascii: "黑体", hAnsi: "黑体", eastAsia: "黑体" } },
        paragraph: { spacing: { before: 240, after: 240, line: 360 }, outlineLevel: 0, keepNext: false, keepLines: false }
      },
      {
        id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 28, bold: true, font: { ascii: "黑体", hAnsi: "黑体", eastAsia: "黑体" } },
        paragraph: { spacing: { before: 180, after: 180, line: 360 }, outlineLevel: 1, keepNext: false, keepLines: false }
      }
    ]
  },
  sections: [{
    properties: {
      page: { margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } }
    },
    children
  }]
});

Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync("d:/PythonProject/密码泄露/LeakGuard/在岗技术革新申报书_铁密_v2.docx", buffer);
  console.log("文档已生成：d:/PythonProject/密码泄露/LeakGuard/在岗技术革新申报书_铁密_v2.docx");
});
