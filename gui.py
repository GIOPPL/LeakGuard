import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import logging
import sys
import time
import secrets
import string

from LeakGuard.email_leak import check_one_email, batch_process_emails_for
from LeakGuard.pass_leak import check_pass_leak, batch_check_pass_leak
from LeakGuard.utils import set_sensitiveWords, set_blacklistUsers, read_file


class TextRedirector:
    def __init__(self, gui):
        self.gui = gui

    def write(self, text):
        if not text:
            return

        def append():
            self.gui.output_text.configure(state=NORMAL)
            self.gui.output_text.insert(END, text)
            self.gui.output_text.see(END)
            self.gui.output_text.configure(state=DISABLED)

        self.gui.root.after(0, append)

    def flush(self):
        pass


class TextHandler(logging.Handler):
    def __init__(self, gui):
        super().__init__()
        self.gui = gui

    def emit(self, record):
        msg = self.format(record)
        level = record.levelname

        def append():
            self.gui.append_log(msg, level)

        self.gui.root.after(0, append)


class LeakGuardGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("铁密 - 综合泄露检测工具")
        self.root.geometry("1100x800")
        self.root.minsize(950, 700)

        # 主题
        self.style = ttk.Style("darkly")

        # 日志
        self.log_text_handler = TextHandler(self)
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[self.log_text_handler]
        )
        self.logger = logging.getLogger(__name__)

        self.running = False
        self.current_tab = "email"
        self.start_time = 0

        self.create_widgets()

        # 重定向 stdout 到 GUI 日志区域（线程安全）
        sys.stdout = TextRedirector(self)

    def create_widgets(self):
        # 主容器
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=BOTH, expand=True)

        # 侧边栏
        self.create_sidebar(main_container)

        # 右侧区域
        right_frame = ttk.Frame(main_container)
        right_frame.pack(side=LEFT, fill=BOTH, expand=True, padx=15, pady=15)

        # 内容区域（卡片）
        self.create_content_cards(right_frame)

        # 日志区域
        self.create_log_area(right_frame)

        # 底部操作栏
        self.create_action_bar(right_frame)

        # 状态栏
        self.create_status_bar(right_frame)

    def create_sidebar(self, parent):
        sidebar = ttk.Frame(parent, width=200)
        sidebar.pack(side=LEFT, fill=Y)
        sidebar.pack_propagate(False)

        # Logo
        logo_frame = ttk.Frame(sidebar)
        logo_frame.pack(fill=X, pady=(25, 5), padx=15)
        ttk.Label(logo_frame, text="🔒", font=("Segoe UI Emoji", 28), foreground="#10B981").pack()
        ttk.Label(logo_frame, text="铁密", font=("Consolas", 16, "bold")).pack()
        ttk.Label(logo_frame, text="综合泄露检测工具", font=("Microsoft YaHei", 9), foreground="#6c757d").pack(pady=(2, 0))

        ttk.Separator(sidebar, bootstyle="secondary").pack(fill=X, padx=15, pady=15)

        # 导航
        self.nav_buttons = {}
        nav_items = [
            ("email", "📧  邮箱检测"),
            ("password", "🔐  密码检测"),
        ]

        for key, label in nav_items:
            btn = ttk.Button(
                sidebar,
                text=label,
                bootstyle="link",
                command=lambda k=key: self.switch_tab(k)
            )
            btn.pack(fill=X, padx=10, pady=2)
            self.nav_buttons[key] = btn

        ttk.Separator(sidebar, bootstyle="secondary").pack(fill=X, padx=15, pady=15)

        settings_btn = ttk.Button(
            sidebar,
            text="⚙️  设置",
            bootstyle="link",
            command=lambda: self.switch_tab("settings")
        )
        settings_btn.pack(fill=X, padx=10, pady=2)
        self.nav_buttons["settings"] = settings_btn

        self.highlight_nav("email")

    def highlight_nav(self, key):
        for k, btn in self.nav_buttons.items():
            if k == key:
                btn.configure(bootstyle="success-link")
            else:
                btn.configure(bootstyle="link")

    def switch_tab(self, key):
        self.current_tab = key
        self.highlight_nav(key)
        for k, frame in self.content_frames.items():
            if k == key:
                frame.pack(fill=BOTH, expand=True)
            else:
                frame.pack_forget()

    def create_content_cards(self, parent):
        self.content_frames = {}

        self.content_frames["email"] = self.build_email_frame(parent)
        self.content_frames["password"] = self.build_password_frame(parent)
        self.content_frames["settings"] = self.build_settings_frame(parent)

        for k, frame in self.content_frames.items():
            if k != "email":
                frame.pack_forget()

    def build_email_frame(self, parent):
        frame = ttk.Frame(parent)

        ttk.Label(frame, text="📧 邮箱泄露检测", font=("Consolas", 18, "bold")).pack(anchor=W, pady=(0, 5))
        ttk.Label(frame, text="检测邮箱是否在公开数据泄露事件中暴露", font=("Microsoft YaHei", 10), foreground="#6c757d").pack(anchor=W, pady=(0, 15))

        card = ttk.Labelframe(frame, text="检测配置", bootstyle="primary")
        card.pack(fill=X, pady=5)

        mode_frame = ttk.Frame(card)
        mode_frame.pack(fill=X, padx=15, pady=(10, 5))
        ttk.Label(mode_frame, text="检测模式:", font=("Microsoft YaHei", 10)).pack(side=LEFT)
        self.email_mode = ttk.StringVar(value="single")
        ttk.Radiobutton(mode_frame, text="单条检测", variable=self.email_mode, value="single", bootstyle="success-toolbutton", command=self.toggle_email_mode).pack(side=LEFT, padx=(10, 5))
        ttk.Radiobutton(mode_frame, text="批量检测", variable=self.email_mode, value="batch", bootstyle="success-toolbutton", command=self.toggle_email_mode).pack(side=LEFT, padx=5)

        self.email_single_frame = ttk.Frame(card)
        self.email_single_frame.pack(fill=X, padx=15, pady=10)
        ttk.Label(self.email_single_frame, text="邮箱地址", font=("Microsoft YaHei", 10)).pack(anchor=W)
        self.email_entry = ttk.Entry(self.email_single_frame)
        self.email_entry.pack(fill=X, pady=(5, 0))

        self.email_batch_frame = ttk.Frame(card)
        ttk.Label(self.email_batch_frame, text="邮箱列表文件", font=("Microsoft YaHei", 10)).pack(anchor=W)
        batch_inner = ttk.Frame(self.email_batch_frame)
        batch_inner.pack(fill=X, pady=(5, 0))
        self.email_file_entry = ttk.Entry(batch_inner)
        self.email_file_entry.pack(side=LEFT, fill=X, expand=True)
        ttk.Button(batch_inner, text="浏览", bootstyle="primary-outline", command=self.browse_email_file).pack(side=LEFT, padx=(8, 0))

        return frame

    def toggle_email_mode(self):
        if self.email_mode.get() == "single":
            self.email_batch_frame.pack_forget()
            self.email_single_frame.pack(fill=X, padx=15, pady=10)
        else:
            self.email_single_frame.pack_forget()
            self.email_batch_frame.pack(fill=X, padx=15, pady=10)

    def build_password_frame(self, parent):
        frame = ttk.Frame(parent)

        ttk.Label(frame, text="🔐 密码泄露检测", font=("Consolas", 18, "bold")).pack(anchor=W, pady=(0, 5))
        ttk.Label(frame, text="检测密码是否在已知泄露数据库中出现", font=("Microsoft YaHei", 10), foreground="#6c757d").pack(anchor=W, pady=(0, 15))

        card = ttk.Labelframe(frame, text="检测配置", bootstyle="danger")
        card.pack(fill=X, pady=5)

        mode_frame = ttk.Frame(card)
        mode_frame.pack(fill=X, padx=15, pady=(10, 5))
        ttk.Label(mode_frame, text="检测模式:").pack(side=LEFT)
        self.pass_mode = ttk.StringVar(value="single")
        ttk.Radiobutton(mode_frame, text="单条检测", variable=self.pass_mode, value="single", bootstyle="danger-toolbutton", command=self.toggle_pass_mode).pack(side=LEFT, padx=(10, 5))
        ttk.Radiobutton(mode_frame, text="批量检测", variable=self.pass_mode, value="batch", bootstyle="danger-toolbutton", command=self.toggle_pass_mode).pack(side=LEFT, padx=5)

        self.pass_single_frame = ttk.Frame(card)
        self.pass_single_frame.pack(fill=X, padx=15, pady=10)
        ttk.Label(self.pass_single_frame, text="密码").pack(anchor=W)
        single_inner = ttk.Frame(self.pass_single_frame)
        single_inner.pack(fill=X, pady=(5, 0))
        self.password_entry = ttk.Entry(single_inner, show="•")
        self.password_entry.pack(side=LEFT, fill=X, expand=True)
        self.pass_check_btn = ttk.Button(single_inner, text="🔍 检测", bootstyle="danger", command=self.check_single_password, width=10)
        self.pass_check_btn.pack(side=LEFT, padx=(8, 0))

        self.pass_batch_frame = ttk.Frame(card)
        ttk.Label(self.pass_batch_frame, text="密码列表文件").pack(anchor=W)
        batch_inner = ttk.Frame(self.pass_batch_frame)
        batch_inner.pack(fill=X, pady=(5, 0))
        self.pass_file_entry = ttk.Entry(batch_inner)
        self.pass_file_entry.pack(side=LEFT, fill=X, expand=True)
        ttk.Button(batch_inner, text="浏览", bootstyle="danger-outline", command=self.browse_pass_file).pack(side=LEFT, padx=(8, 0))

        # 随机密码生成器卡片
        gen_card = ttk.Labelframe(frame, text="🔧 随机密码生成器", bootstyle="info")
        gen_card.pack(fill=X, pady=(15, 5))

        gen_inner = ttk.Frame(gen_card)
        gen_inner.pack(fill=X, padx=15, pady=15)

        # 长度设置
        len_frame = ttk.Frame(gen_inner)
        len_frame.pack(fill=X, pady=(0, 10))
        ttk.Label(len_frame, text="密码长度:", font=("Microsoft YaHei", 10)).pack(side=LEFT)
        self.pass_len_var = tk.IntVar(value=16)
        self.pass_len_scale = ttk.Scale(len_frame, from_=8, to=32, variable=self.pass_len_var, orient=HORIZONTAL, length=200, command=self._on_pass_len_change)
        self.pass_len_scale.pack(side=LEFT, padx=(10, 5))
        self.pass_len_label = ttk.Label(len_frame, text="16", font=("Consolas", 11, "bold"), foreground="#3B82F6")
        self.pass_len_label.pack(side=LEFT)

        # 字符类型
        char_frame = ttk.Frame(gen_inner)
        char_frame.pack(fill=X, pady=(0, 10))
        ttk.Label(char_frame, text="包含字符:", font=("Microsoft YaHei", 10)).pack(anchor=W)
        char_inner = ttk.Frame(char_frame)
        char_inner.pack(fill=X, pady=(5, 0))
        self.use_upper = tk.BooleanVar(value=True)
        self.use_lower = tk.BooleanVar(value=True)
        self.use_digit = tk.BooleanVar(value=True)
        self.use_special = tk.BooleanVar(value=True)
        ttk.Checkbutton(char_inner, text="大写字母", variable=self.use_upper, bootstyle="info-round-toggle").pack(side=LEFT, padx=(0, 10))
        ttk.Checkbutton(char_inner, text="小写字母", variable=self.use_lower, bootstyle="info-round-toggle").pack(side=LEFT, padx=(0, 10))
        ttk.Checkbutton(char_inner, text="数字", variable=self.use_digit, bootstyle="info-round-toggle").pack(side=LEFT, padx=(0, 10))
        ttk.Checkbutton(char_inner, text="特殊符号", variable=self.use_special, bootstyle="info-round-toggle").pack(side=LEFT, padx=(0, 10))

        # 生成结果
        result_frame = ttk.Frame(gen_inner)
        result_frame.pack(fill=X, pady=(0, 10))
        ttk.Label(result_frame, text="生成结果:", font=("Microsoft YaHei", 10)).pack(anchor=W)
        result_inner = ttk.Frame(result_frame)
        result_inner.pack(fill=X, pady=(5, 0))
        self.gen_password_entry = ttk.Entry(result_inner, font=("Consolas", 11))
        self.gen_password_entry.pack(side=LEFT, fill=X, expand=True)
        ttk.Button(result_inner, text="📋", bootstyle="info-outline", command=self.copy_password, width=4).pack(side=LEFT, padx=(8, 0))

        # 生成按钮
        ttk.Button(gen_inner, text="🎲 生成密码", bootstyle="info", command=self.generate_password, width=20).pack(pady=(5, 0))

        return frame

    def toggle_pass_mode(self):
        if self.pass_mode.get() == "single":
            self.pass_batch_frame.pack_forget()
            self.pass_single_frame.pack(fill=X, padx=15, pady=10)
        else:
            self.pass_single_frame.pack_forget()
            self.pass_batch_frame.pack(fill=X, padx=15, pady=10)

    def build_google_frame(self, parent):
        frame = ttk.Frame(parent)

        ttk.Label(frame, text="🔍 Google 邮箱搜索", font=("Consolas", 18, "bold")).pack(anchor=W, pady=(0, 5))
        ttk.Label(frame, text="通过 Google 搜索提取指定域名的邮箱地址", font=("Microsoft YaHei", 10), foreground="#6c757d").pack(anchor=W, pady=(0, 15))

        card = ttk.Labelframe(frame, text="搜索配置", bootstyle="warning")
        card.pack(fill=X, pady=5)

        mode_frame = ttk.Frame(card)
        mode_frame.pack(fill=X, padx=15, pady=(10, 5))
        ttk.Label(mode_frame, text="搜索模式:").pack(side=LEFT)
        self.google_mode = ttk.StringVar(value="single")
        ttk.Radiobutton(mode_frame, text="单条后缀", variable=self.google_mode, value="single", bootstyle="warning-toolbutton", command=self.toggle_google_mode).pack(side=LEFT, padx=(10, 5))
        ttk.Radiobutton(mode_frame, text="批量后缀", variable=self.google_mode, value="batch", bootstyle="warning-toolbutton", command=self.toggle_google_mode).pack(side=LEFT, padx=5)

        self.google_single_frame = ttk.Frame(card)
        self.google_single_frame.pack(fill=X, padx=15, pady=10)
        ttk.Label(self.google_single_frame, text="邮箱后缀").pack(anchor=W)
        self.google_suffix_entry = ttk.Entry(self.google_single_frame)
        self.google_suffix_entry.pack(fill=X, pady=(5, 0))

        self.google_batch_frame = ttk.Frame(card)
        ttk.Label(self.google_batch_frame, text="后缀列表文件").pack(anchor=W)
        batch_inner = ttk.Frame(self.google_batch_frame)
        batch_inner.pack(fill=X, pady=(5, 0))
        self.google_file_entry = ttk.Entry(batch_inner)
        self.google_file_entry.pack(side=LEFT, fill=X, expand=True)
        ttk.Button(batch_inner, text="浏览", bootstyle="warning-outline", command=self.browse_google_file).pack(side=LEFT, padx=(8, 0))

        return frame

    def toggle_google_mode(self):
        if self.google_mode.get() == "single":
            self.google_batch_frame.pack_forget()
            self.google_single_frame.pack(fill=X, padx=15, pady=10)
        else:
            self.google_single_frame.pack_forget()
            self.google_batch_frame.pack(fill=X, padx=15, pady=10)

    def build_github_frame(self, parent):
        frame = ttk.Frame(parent)

        ttk.Label(frame, text="🐙 GitHub 代码搜索", font=("Consolas", 18, "bold")).pack(anchor=W, pady=(0, 5))
        ttk.Label(frame, text="在 GitHub 上搜索包含敏感信息的代码仓库", font=("Microsoft YaHei", 10), foreground="#6c757d").pack(anchor=W, pady=(0, 15))

        card = ttk.Labelframe(frame, text="搜索配置", bootstyle="info")
        card.pack(fill=X, pady=5)

        mode_frame = ttk.Frame(card)
        mode_frame.pack(fill=X, padx=15, pady=(10, 5))
        ttk.Label(mode_frame, text="搜索模式:").pack(side=LEFT)
        self.github_mode = ttk.StringVar(value="single")
        ttk.Radiobutton(mode_frame, text="单条关键字", variable=self.github_mode, value="single", bootstyle="info-toolbutton", command=self.toggle_github_mode).pack(side=LEFT, padx=(10, 5))
        ttk.Radiobutton(mode_frame, text="批量关键字", variable=self.github_mode, value="batch", bootstyle="info-toolbutton", command=self.toggle_github_mode).pack(side=LEFT, padx=5)

        self.github_single_frame = ttk.Frame(card)
        self.github_single_frame.pack(fill=X, padx=15, pady=10)
        ttk.Label(self.github_single_frame, text="搜索关键字").pack(anchor=W)
        self.github_query_entry = ttk.Entry(self.github_single_frame)
        self.github_query_entry.pack(fill=X, pady=(5, 0))

        self.github_batch_frame = ttk.Frame(card)
        ttk.Label(self.github_batch_frame, text="关键字列表文件").pack(anchor=W)
        batch_inner = ttk.Frame(self.github_batch_frame)
        batch_inner.pack(fill=X, pady=(5, 0))
        self.github_file_entry = ttk.Entry(batch_inner)
        self.github_file_entry.pack(side=LEFT, fill=X, expand=True)
        ttk.Button(batch_inner, text="浏览", bootstyle="info-outline", command=self.browse_github_file).pack(side=LEFT, padx=(8, 0))

        return frame

    def toggle_github_mode(self):
        if self.github_mode.get() == "single":
            self.github_batch_frame.pack_forget()
            self.github_single_frame.pack(fill=X, padx=15, pady=10)
        else:
            self.github_single_frame.pack_forget()
            self.github_batch_frame.pack(fill=X, padx=15, pady=10)

    def build_hunter_frame(self, parent):
        frame = ttk.Frame(parent)

        ttk.Label(frame, text="🌐 Hunter 邮箱搜索", font=("Consolas", 18, "bold")).pack(anchor=W, pady=(0, 5))
        ttk.Label(frame, text="通过 hunter.io 搜索企业域名关联的邮箱地址", font=("Microsoft YaHei", 10), foreground="#6c757d").pack(anchor=W, pady=(0, 15))

        card = ttk.Labelframe(frame, text="搜索配置", bootstyle="success")
        card.pack(fill=X, pady=5)

        inner = ttk.Frame(card)
        inner.pack(fill=X, padx=15, pady=15)
        ttk.Label(inner, text="目标域名").pack(anchor=W)
        self.hunter_domain_entry = ttk.Entry(inner)
        self.hunter_domain_entry.pack(fill=X, pady=(5, 0))

        return frame

    def build_settings_frame(self, parent):
        frame = ttk.Frame(parent)

        ttk.Label(frame, text="⚙️ 全局设置", font=("Consolas", 18, "bold")).pack(anchor=W, pady=(0, 5))
        ttk.Label(frame, text="配置输出格式、黑名单和敏感词", font=("Microsoft YaHei", 10), foreground="#6c757d").pack(anchor=W, pady=(0, 15))

        out_card = ttk.Labelframe(frame, text="输出配置", bootstyle="secondary")
        out_card.pack(fill=X, pady=5)

        inner = ttk.Frame(out_card)
        inner.pack(fill=X, padx=15, pady=15)

        ttk.Label(inner, text="输出文件名").grid(row=0, column=0, sticky=W)
        self.output_entry = ttk.Entry(inner)
        self.output_entry.grid(row=0, column=1, sticky=EW, padx=(10, 0), pady=5)
        inner.columnconfigure(1, weight=1)

        fmt_frame = ttk.Frame(inner)
        fmt_frame.grid(row=1, column=0, columnspan=2, sticky=W, pady=5)
        ttk.Label(fmt_frame, text="输出格式:").pack(side=LEFT)
        self.output_format = ttk.StringVar(value="xlsx")
        ttk.Radiobutton(fmt_frame, text="XLSX", variable=self.output_format, value="xlsx", bootstyle="secondary-toolbutton").pack(side=LEFT, padx=(10, 5))
        ttk.Radiobutton(fmt_frame, text="JSON", variable=self.output_format, value="json", bootstyle="secondary-toolbutton").pack(side=LEFT, padx=5)

        bl_card = ttk.Labelframe(frame, text="黑名单设置", bootstyle="secondary")
        bl_card.pack(fill=X, pady=5)

        bl_inner = ttk.Frame(bl_card)
        bl_inner.pack(fill=X, padx=15, pady=15)
        ttk.Label(bl_inner, text="黑名单文件").pack(anchor=W)
        bl_row = ttk.Frame(bl_inner)
        bl_row.pack(fill=X, pady=(5, 0))
        self.blacklist_file_entry = ttk.Entry(bl_row)
        self.blacklist_file_entry.pack(side=LEFT, fill=X, expand=True)
        ttk.Button(bl_row, text="浏览", bootstyle="secondary-outline", command=self.browse_blacklist_file).pack(side=LEFT, padx=(8, 0))

        sw_card = ttk.Labelframe(frame, text="敏感词设置", bootstyle="secondary")
        sw_card.pack(fill=X, pady=5)

        sw_inner = ttk.Frame(sw_card)
        sw_inner.pack(fill=X, padx=15, pady=15)
        ttk.Label(sw_inner, text="敏感词文件").pack(anchor=W)
        sw_row = ttk.Frame(sw_inner)
        sw_row.pack(fill=X, pady=(5, 0))
        self.sensitive_file_entry = ttk.Entry(sw_row)
        self.sensitive_file_entry.pack(side=LEFT, fill=X, expand=True)
        ttk.Button(sw_row, text="浏览", bootstyle="secondary-outline", command=self.browse_sensitive_file).pack(side=LEFT, padx=(8, 0))

        return frame

    def create_log_area(self, parent):
        log_frame = ttk.Labelframe(parent, text="📋 输出控制台", bootstyle="dark")
        log_frame.pack(fill=BOTH, expand=True, pady=(15, 5))

        text_frame = ttk.Frame(log_frame)
        text_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)

        self.output_text = tk.Text(text_frame, height=12, wrap=WORD, font=("Consolas", 10), state=DISABLED)
        scrollbar = ttk.Scrollbar(text_frame, command=self.output_text.yview)
        self.output_text.configure(yscrollcommand=scrollbar.set)

        self.output_text.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill=Y)

        self.output_text.tag_config("INFO", foreground="#10B981")
        self.output_text.tag_config("WARNING", foreground="#F59E0B")
        self.output_text.tag_config("ERROR", foreground="#EF4444")
        self.output_text.tag_config("DEBUG", foreground="#6c757d")

    def append_log(self, msg, level="INFO"):
        self.output_text.configure(state=NORMAL)
        self.output_text.insert(END, f"{msg}\n", level)
        self.output_text.see(END)
        self.output_text.configure(state=DISABLED)

    def create_action_bar(self, parent):
        bar = ttk.Frame(parent)
        bar.pack(fill=X, pady=5)

        self.run_button = ttk.Button(bar, text="▶  开始检测", bootstyle="success", command=self.run_detection, width=15)
        self.run_button.pack(side=LEFT, padx=(0, 10))

        self.stop_button = ttk.Button(bar, text="⏹  停止", bootstyle="danger", command=self.stop_detection, state=DISABLED, width=12)
        self.stop_button.pack(side=LEFT, padx=5)

        self.progress = ttk.Progressbar(bar, mode="indeterminate", bootstyle="success")
        self.progress.pack(side=LEFT, fill=X, expand=True, padx=10)

        ttk.Button(bar, text="🗑  清空日志", bootstyle="outline", command=self.clear_output).pack(side=RIGHT)

    def create_status_bar(self, parent):
        self.status_bar = ttk.Frame(parent)
        self.status_bar.pack(fill=X, pady=(5, 0))

        self.status_icon = ttk.Label(self.status_bar, text="🟢", font=("Segoe UI Emoji", 12))
        self.status_icon.pack(side=LEFT)

        self.status_text = ttk.Label(self.status_bar, text="就绪", font=("Microsoft YaHei", 10))
        self.status_text.pack(side=LEFT, padx=5)

        self.time_label = ttk.Label(self.status_bar, text="", font=("Consolas", 10), foreground="#6c757d")
        self.time_label.pack(side=RIGHT)

    def set_status(self, status, icon="🟢"):
        self.status_icon.configure(text=icon)
        self.status_text.configure(text=status)

    def clear_output(self):
        self.output_text.configure(state=NORMAL)
        self.output_text.delete("1.0", END)
        self.output_text.configure(state=DISABLED)

    def browse_email_file(self):
        filename = filedialog.askopenfilename(title="选择邮箱文件", filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if filename:
            self.email_file_entry.delete(0, END)
            self.email_file_entry.insert(0, filename)

    def browse_pass_file(self):
        filename = filedialog.askopenfilename(title="选择密码文件", filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if filename:
            self.pass_file_entry.delete(0, END)
            self.pass_file_entry.insert(0, filename)

    def browse_google_file(self):
        filename = filedialog.askopenfilename(title="选择邮箱后缀文件", filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if filename:
            self.google_file_entry.delete(0, END)
            self.google_file_entry.insert(0, filename)

    def browse_github_file(self):
        filename = filedialog.askopenfilename(title="选择关键字文件", filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if filename:
            self.github_file_entry.delete(0, END)
            self.github_file_entry.insert(0, filename)

    def browse_blacklist_file(self):
        filename = filedialog.askopenfilename(title="选择黑名单文件", filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if filename:
            self.blacklist_file_entry.delete(0, END)
            self.blacklist_file_entry.insert(0, filename)

    def browse_sensitive_file(self):
        filename = filedialog.askopenfilename(title="选择敏感词文件", filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if filename:
            self.sensitive_file_entry.delete(0, END)
            self.sensitive_file_entry.insert(0, filename)

    def check_single_password(self):
        password = self.password_entry.get()
        if not password:
            messagebox.showwarning("提示", "请输入要检测的密码")
            return
        self.pass_check_btn.configure(state=DISABLED, text="检测中...")
        thread = threading.Thread(target=self._check_single_password_thread, args=(password,), daemon=True)
        thread.start()

    def _check_single_password_thread(self, password):
        try:
            check_pass_leak(password)
        finally:
            self.root.after(0, self._reset_pass_check_btn)

    def _reset_pass_check_btn(self):
        self.pass_check_btn.configure(state=NORMAL, text="🔍 检测")

    def _on_pass_len_change(self, value):
        self.pass_len_label.configure(text=f"{int(float(value))}")

    def generate_password(self):
        length = self.pass_len_var.get()
        chars = ""
        if self.use_upper.get():
            chars += string.ascii_uppercase
        if self.use_lower.get():
            chars += string.ascii_lowercase
        if self.use_digit.get():
            chars += string.digits
        if self.use_special.get():
            chars += "!@#$%^&*()_+-=[]{}|;:,.<>?"

        if not chars:
            messagebox.showwarning("提示", "请至少选择一种字符类型")
            return

        # 确保每种选中的类型至少出现一次
        password_chars = []
        selected_sets = []
        if self.use_upper.get():
            selected_sets.append(string.ascii_uppercase)
        if self.use_lower.get():
            selected_sets.append(string.ascii_lowercase)
        if self.use_digit.get():
            selected_sets.append(string.digits)
        if self.use_special.get():
            selected_sets.append("!@#$%^&*()_+-=[]{}|;:,.<>?")

        for s in selected_sets:
            password_chars.append(secrets.choice(s))

        for _ in range(length - len(selected_sets)):
            password_chars.append(secrets.choice(chars))

        secrets.SystemRandom().shuffle(password_chars)
        password = "".join(password_chars)

        self.gen_password_entry.delete(0, END)
        self.gen_password_entry.insert(0, password)

    def copy_password(self):
        password = self.gen_password_entry.get()
        if password:
            self.root.clipboard_clear()
            self.root.clipboard_append(password)
            self.root.update()
            messagebox.showinfo("提示", "密码已复制到剪贴板")

    def run_detection(self):
        self.running = True
        self.start_time = time.time()
        self.run_button.configure(state=DISABLED)
        self.stop_button.configure(state=NORMAL)
        self.progress.start()
        self.set_status("运行中...", "🟡")

        thread = threading.Thread(target=self._run_detection_thread, daemon=True)
        thread.start()

        self._update_time()

    def _update_time(self):
        if self.running:
            elapsed = time.time() - self.start_time
            self.time_label.configure(text=f"⏱ {elapsed:.1f}s")
            self.root.after(500, self._update_time)

    def _setup_blacklist_and_sensitive_words(self):
        if self.blacklist_file_entry.get():
            try:
                blacklist_users = read_file(self.blacklist_file_entry.get())
                set_blacklistUsers(blacklist_users)
                self.logger.info(f"已加载 {len(blacklist_users)} 个黑名单用户")
            except Exception as e:
                self.logger.error(f"加载黑名单用户文件失败: {str(e)}")

        if self.sensitive_file_entry.get():
            try:
                sensitive_words = read_file(self.sensitive_file_entry.get())
                set_sensitiveWords(sensitive_words)
                self.logger.info(f"已加载 {len(sensitive_words)} 个敏感词")
            except Exception as e:
                self.logger.error(f"加载敏感词文件失败: {str(e)}")

    def _run_detection_thread(self):
        try:
            self.logger.info("=" * 50)
            self.logger.info("开始泄露检测...")

            output_file = self.output_entry.get() if self.output_entry.get() else None
            mode = self.output_format.get()

            executed = False

            if self.current_tab == "email":
                if self.email_mode.get() == "single" and self.email_entry.get():
                    self.logger.info("执行邮箱泄露检测...")
                    check_one_email(self.email_entry.get(), output_file, mode)
                    executed = True
                elif self.email_mode.get() == "batch" and self.email_file_entry.get():
                    self.logger.info("执行批量邮箱泄露检测...")
                    batch_process_emails_for(self.email_file_entry.get(), output_file, mode)
                    executed = True

            elif self.current_tab == "password":
                if self.pass_mode.get() == "single" and self.password_entry.get():
                    self.logger.info("执行密码泄露检测...")
                    check_pass_leak(self.password_entry.get())
                    executed = True
                elif self.pass_mode.get() == "batch" and self.pass_file_entry.get():
                    self.logger.info("执行批量密码泄露检测...")
                    batch_check_pass_leak(self.pass_file_entry.get())
                    executed = True

            self._setup_blacklist_and_sensitive_words()

            if not executed:
                self.logger.warning("未选择任何检测项目，请填写输入内容后再运行")
            else:
                self.logger.info("检测完成！")

            self.logger.info("=" * 50)

        except Exception as e:
            self.logger.error(f"检测过程中发生错误: {str(e)}")
        finally:
            self.running = False
            self.root.after(0, self._enable_buttons)

    def _enable_buttons(self):
        self.run_button.configure(state=NORMAL)
        self.stop_button.configure(state=DISABLED)
        self.progress.stop()
        self.set_status("就绪", "🟢")
        self.time_label.configure(text="")

    def stop_detection(self):
        self.running = False
        self.logger.info("检测已停止")
        self._enable_buttons()


def main():
    root = ttk.Window(themename="darkly")
    app = LeakGuardGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
