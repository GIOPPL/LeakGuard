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
import os
import math
import base64
import ctypes
import random
import json
from urllib.parse import urlparse

from LeakGuard.email_leak import check_one_email, batch_process_emails_for
from LeakGuard.pass_leak import check_pass_leak, batch_check_pass_leak
from LeakGuard.utils import set_sensitiveWords, set_blacklistUsers, read_file
from deepseek_client import DeepSeekClient

from pypdf import PdfReader, PdfWriter
from pypdf.constants import UserAccessPermissions
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from PIL import Image, ImageGrab
import cv2
from pyzbar.pyzbar import decode
import psutil
import pyperclip


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

        # 加载 DeepSeek 配置
        self.config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", "config.json")
        self.deepseek_config = self._load_deepseek_config()

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

        ttk.Separator(sidebar, bootstyle="secondary").pack(fill=X, padx=15, pady=10)

        tool_items = [
            ("pass_tools", "🔑  密码工具"),
            ("pdf", "📄  PDF 加解密"),
            ("aes", "🔑  文本加解密"),
            ("stego", "🖼️  图片隐写检测"),
            ("qr", "📷  二维码解析"),
            ("port", "🌐  端口快照"),
            ("clipboard", "🛡️  剪贴板哨兵"),
            ("shred", "🗑️  文件粉碎"),
        ]

        for key, label in tool_items:
            btn = ttk.Button(
                sidebar,
                text=label,
                bootstyle="link",
                command=lambda k=key: self.switch_tab(k)
            )
            btn.pack(fill=X, padx=10, pady=2)
            self.nav_buttons[key] = btn

        ttk.Separator(sidebar, bootstyle="secondary").pack(fill=X, padx=15, pady=10)

        settings_btn = ttk.Button(
            sidebar,
            text="⚙️  设置",
            bootstyle="link",
            command=lambda: self.switch_tab("settings")
        )
        settings_btn.pack(fill=X, padx=10, pady=2)
        self.nav_buttons["settings"] = settings_btn

        self.highlight_nav(self.current_tab)

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

        # 日志区域在除密码工具外的所有页面可见
        if key in ("pass_tools",):
            self.log_frame.pack_forget()
        else:
            self.log_frame.pack(fill=BOTH, expand=True, pady=(15, 5))
        if key in ("email", "password"):
            self.action_bar.pack(fill=X, pady=5)
            self.status_bar.pack(fill=X, pady=(5, 0))
        else:
            self.action_bar.pack_forget()
            self.status_bar.pack_forget()

    def create_content_cards(self, parent):
        self.content_frames = {}

        self.content_frames["email"] = self.build_email_frame(parent)
        self.content_frames["password"] = self.build_password_frame(parent)
        self.content_frames["pass_tools"] = self.build_password_tools_frame(parent)
        self.content_frames["pdf"] = self.build_pdf_frame(parent)
        self.content_frames["aes"] = self.build_aes_frame(parent)
        self.content_frames["stego"] = self.build_stego_frame(parent)
        self.content_frames["qr"] = self.build_qr_frame(parent)
        self.content_frames["port"] = self.build_port_frame(parent)
        self.content_frames["clipboard"] = self.build_clipboard_frame(parent)
        self.content_frames["shred"] = self.build_shred_frame(parent)
        self.content_frames["settings"] = self.build_settings_frame(parent)

        for k, frame in self.content_frames.items():
            if k == self.current_tab:
                frame.pack(fill=BOTH, expand=True)
            else:
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

        return frame

    def toggle_pass_mode(self):
        if self.pass_mode.get() == "single":
            self.pass_batch_frame.pack_forget()
            self.pass_single_frame.pack(fill=X, padx=15, pady=10)
        else:
            self.pass_single_frame.pack_forget()
            self.pass_batch_frame.pack(fill=X, padx=15, pady=10)

    def build_password_tools_frame(self, parent):
        frame = ttk.Frame(parent)

        ttk.Label(frame, text="🔑 密码工具箱", font=("Consolas", 18, "bold")).pack(anchor=W, pady=(0, 5))
        ttk.Label(frame, text="随机密码生成与 AI 智能优化", font=("Microsoft YaHei", 10), foreground="#6c757d").pack(anchor=W, pady=(0, 15))

        # 随机密码生成器卡片
        gen_card = ttk.Labelframe(frame, text="🔧 随机密码生成器", bootstyle="info")
        gen_card.pack(fill=X, pady=5)

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

        # AI 智能密码优化卡片
        ai_opt_card = ttk.Labelframe(frame, text="🤖 AI 智能密码优化", bootstyle="success")
        ai_opt_card.pack(fill=X, pady=(15, 5))

        ai_opt_inner = ttk.Frame(ai_opt_card)
        ai_opt_inner.pack(fill=X, padx=15, pady=15)

        ttk.Label(ai_opt_inner, text="输入密码风格或关键词（如：我的猫叫咪咪、公司缩写+生日）", font=("Microsoft YaHei", 10)).pack(anchor=W)
        self.ai_opt_input = ttk.Entry(ai_opt_inner, font=("Microsoft YaHei", 10))
        self.ai_opt_input.pack(fill=X, pady=(5, 0))
        ttk.Button(ai_opt_inner, text="🔍 分析并优化", bootstyle="success", command=self._ai_optimize_password).pack(anchor=W, pady=(10, 0))

        # AI 生成结果区域
        self.ai_result_frame = ttk.Labelframe(ai_opt_inner, text="生成结果", bootstyle="success")
        self.ai_result_frame.pack(fill=X, pady=(10, 0))
        self.ai_result_frame.pack_forget()  # 初始隐藏

        self.ai_password_vars = []
        self.ai_password_entries = []
        result_grid = ttk.Frame(self.ai_result_frame)
        result_grid.pack(fill=X, padx=10, pady=10)

        for row in range(5):
            for col in range(2):
                idx = row * 2 + col
                cell = ttk.Frame(result_grid)
                cell.grid(row=row, column=col, sticky=EW, padx=5, pady=3)
                result_grid.columnconfigure(col, weight=1)

                var = tk.StringVar()
                self.ai_password_vars.append(var)
                entry = ttk.Entry(cell, textvariable=var, font=("Consolas", 10), state="readonly")
                entry.pack(side=LEFT, fill=X, expand=True)
                self.ai_password_entries.append(entry)

                ttk.Button(cell, text="📋", bootstyle="success-outline", command=lambda v=var: self._copy_ai_password(v), width=4).pack(side=LEFT, padx=(5, 0))

        # AI 建议文本
        self.ai_suggestion_label = ttk.Label(self.ai_result_frame, text="", font=("Microsoft YaHei", 9), foreground="#6c757d", wraplength=800)
        self.ai_suggestion_label.pack(anchor=W, padx=10, pady=(0, 10))

        return frame

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

    def build_pdf_frame(self, parent):
        frame = ttk.Frame(parent)

        ttk.Label(frame, text="📄 PDF 加密/解密", font=("Consolas", 18, "bold")).pack(anchor=W, pady=(0, 5))
        ttk.Label(frame, text="给 PDF 文件设置密码或移除密码保护", font=("Microsoft YaHei", 10), foreground="#6c757d").pack(anchor=W, pady=(0, 15))

        card = ttk.Labelframe(frame, text="操作配置", bootstyle="warning")
        card.pack(fill=X, pady=5)

        mode_frame = ttk.Frame(card)
        mode_frame.pack(fill=X, padx=15, pady=(10, 5))
        ttk.Label(mode_frame, text="操作模式:", font=("Microsoft YaHei", 10)).pack(side=LEFT)
        self.pdf_mode = ttk.StringVar(value="encrypt")
        ttk.Radiobutton(mode_frame, text="加密", variable=self.pdf_mode, value="encrypt", bootstyle="warning-toolbutton", command=self.toggle_pdf_mode).pack(side=LEFT, padx=(10, 5))
        ttk.Radiobutton(mode_frame, text="解密", variable=self.pdf_mode, value="decrypt", bootstyle="warning-toolbutton", command=self.toggle_pdf_mode).pack(side=LEFT, padx=5)

        self.pdf_encrypt_frame = ttk.Frame(card)
        self.pdf_encrypt_frame.pack(fill=X, padx=15, pady=10)
        ttk.Label(self.pdf_encrypt_frame, text="选择 PDF 文件", font=("Microsoft YaHei", 10)).pack(anchor=W)
        f1 = ttk.Frame(self.pdf_encrypt_frame)
        f1.pack(fill=X, pady=(5, 0))
        self.pdf_file_entry = ttk.Entry(f1)
        self.pdf_file_entry.pack(side=LEFT, fill=X, expand=True)
        ttk.Button(f1, text="浏览", bootstyle="warning-outline", command=self.browse_pdf_file).pack(side=LEFT, padx=(8, 0))

        ttk.Label(self.pdf_encrypt_frame, text="打开密码（可选）", font=("Microsoft YaHei", 10)).pack(anchor=W, pady=(10, 0))
        self.pdf_open_pass = ttk.Entry(self.pdf_encrypt_frame, show="•")
        self.pdf_open_pass.pack(fill=X, pady=(5, 0))

        ttk.Label(self.pdf_encrypt_frame, text="权限密码（可选）", font=("Microsoft YaHei", 10)).pack(anchor=W, pady=(10, 0))
        self.pdf_perm_pass = ttk.Entry(self.pdf_encrypt_frame, show="•")
        self.pdf_perm_pass.pack(fill=X, pady=(5, 0))

        perm_frame = ttk.Frame(self.pdf_encrypt_frame)
        perm_frame.pack(fill=X, pady=(10, 0))
        self.pdf_no_print = tk.BooleanVar(value=False)
        self.pdf_no_copy = tk.BooleanVar(value=False)
        self.pdf_no_edit = tk.BooleanVar(value=False)
        ttk.Checkbutton(perm_frame, text="禁止打印", variable=self.pdf_no_print, bootstyle="warning-round-toggle").pack(side=LEFT, padx=(0, 10))
        ttk.Checkbutton(perm_frame, text="禁止复制", variable=self.pdf_no_copy, bootstyle="warning-round-toggle").pack(side=LEFT, padx=(0, 10))
        ttk.Checkbutton(perm_frame, text="禁止编辑", variable=self.pdf_no_edit, bootstyle="warning-round-toggle").pack(side=LEFT, padx=(0, 10))

        ttk.Label(self.pdf_encrypt_frame, text="输出文件名", font=("Microsoft YaHei", 10)).pack(anchor=W, pady=(10, 0))
        self.pdf_out_entry = ttk.Entry(self.pdf_encrypt_frame)
        self.pdf_out_entry.pack(fill=X, pady=(5, 0))

        ttk.Button(self.pdf_encrypt_frame, text="🔒 执行加密", bootstyle="warning", command=self.pdf_process, width=20).pack(pady=(15, 0))

        self.pdf_decrypt_frame = ttk.Frame(card)
        ttk.Label(self.pdf_decrypt_frame, text="选择 PDF 文件", font=("Microsoft YaHei", 10)).pack(anchor=W)
        f2 = ttk.Frame(self.pdf_decrypt_frame)
        f2.pack(fill=X, pady=(5, 0))
        self.pdf_decrypt_file_entry = ttk.Entry(f2)
        self.pdf_decrypt_file_entry.pack(side=LEFT, fill=X, expand=True)
        ttk.Button(f2, text="浏览", bootstyle="warning-outline", command=self.browse_pdf_decrypt_file).pack(side=LEFT, padx=(8, 0))

        ttk.Label(self.pdf_decrypt_frame, text="打开密码", font=("Microsoft YaHei", 10)).pack(anchor=W, pady=(10, 0))
        self.pdf_decrypt_pass = ttk.Entry(self.pdf_decrypt_frame, show="•")
        self.pdf_decrypt_pass.pack(fill=X, pady=(5, 0))

        ttk.Label(self.pdf_decrypt_frame, text="输出文件名", font=("Microsoft YaHei", 10)).pack(anchor=W, pady=(10, 0))
        self.pdf_decrypt_out_entry = ttk.Entry(self.pdf_decrypt_frame)
        self.pdf_decrypt_out_entry.pack(fill=X, pady=(5, 0))

        ttk.Button(self.pdf_decrypt_frame, text="🔓 执行解密", bootstyle="warning", command=self.pdf_decrypt_process, width=20).pack(pady=(15, 0))

        return frame

    def toggle_pdf_mode(self):
        if self.pdf_mode.get() == "encrypt":
            self.pdf_decrypt_frame.pack_forget()
            self.pdf_encrypt_frame.pack(fill=X, padx=15, pady=10)
        else:
            self.pdf_encrypt_frame.pack_forget()
            self.pdf_decrypt_frame.pack(fill=X, padx=15, pady=10)

    def build_aes_frame(self, parent):
        frame = ttk.Frame(parent)

        ttk.Label(frame, text="🔑 敏感文本 AES 加解密", font=("Consolas", 18, "bold")).pack(anchor=W, pady=(0, 5))
        ttk.Label(frame, text="安全地加密和分享敏感信息", font=("Microsoft YaHei", 10), foreground="#6c757d").pack(anchor=W, pady=(0, 15))

        mode_card = ttk.Labelframe(frame, text="操作模式", bootstyle="info")
        mode_card.pack(fill=X, pady=5)
        mode_inner = ttk.Frame(mode_card)
        mode_inner.pack(fill=X, padx=15, pady=10)
        self.aes_mode = ttk.StringVar(value="encrypt")
        ttk.Radiobutton(mode_inner, text="加密模式", variable=self.aes_mode, value="encrypt", bootstyle="info-toolbutton", command=self.toggle_aes_mode).pack(side=LEFT, padx=(0, 10))
        ttk.Radiobutton(mode_inner, text="解密模式", variable=self.aes_mode, value="decrypt", bootstyle="info-toolbutton", command=self.toggle_aes_mode).pack(side=LEFT, padx=(0, 10))

        self.aes_encrypt_frame = ttk.Frame(frame)
        self.aes_encrypt_frame.pack(fill=X, pady=5)
        enc_card = ttk.Labelframe(self.aes_encrypt_frame, text="🔐 加密", bootstyle="info")
        enc_card.pack(fill=X, pady=5)
        enc_inner = ttk.Frame(enc_card)
        enc_inner.pack(fill=X, padx=15, pady=10)
        ttk.Label(enc_inner, text="待加密文本", font=("Microsoft YaHei", 10)).pack(anchor=W)
        self.aes_plain_text = tk.Text(enc_inner, height=5, wrap=WORD, font=("Consolas", 10))
        self.aes_plain_text.pack(fill=X, pady=(5, 0))
        ttk.Label(enc_inner, text="密码", font=("Microsoft YaHei", 10)).pack(anchor=W, pady=(10, 0))
        self.aes_enc_pass = ttk.Entry(enc_inner, show="•")
        self.aes_enc_pass.pack(fill=X, pady=(5, 0))
        ttk.Label(enc_inner, text="加密结果（Base64）", font=("Microsoft YaHei", 10)).pack(anchor=W, pady=(10, 0))
        self.aes_enc_result = tk.Text(enc_inner, height=3, wrap=WORD, font=("Consolas", 10))
        self.aes_enc_result.pack(fill=X, pady=(5, 0))
        btn_frame = ttk.Frame(enc_inner)
        btn_frame.pack(fill=X, pady=(10, 0))
        ttk.Button(btn_frame, text="🔒 执行加密", bootstyle="info", command=self.aes_encrypt).pack(side=LEFT, padx=(0, 10))
        ttk.Button(btn_frame, text="📋 复制结果", bootstyle="info-outline", command=self.aes_copy_enc_result).pack(side=LEFT, padx=(0, 10))
        ttk.Button(btn_frame, text="🗑 清空", bootstyle="outline", command=self.aes_clear_encrypt).pack(side=LEFT)

        self.aes_decrypt_frame = ttk.Frame(frame)
        dec_card = ttk.Labelframe(self.aes_decrypt_frame, text="🔓 解密", bootstyle="info")
        dec_card.pack(fill=X, pady=5)
        dec_inner = ttk.Frame(dec_card)
        dec_inner.pack(fill=X, padx=15, pady=10)
        ttk.Label(dec_inner, text="待解密文本（Base64）", font=("Microsoft YaHei", 10)).pack(anchor=W)
        self.aes_cipher_text = tk.Text(dec_inner, height=5, wrap=WORD, font=("Consolas", 10))
        self.aes_cipher_text.pack(fill=X, pady=(5, 0))
        ttk.Label(dec_inner, text="密码", font=("Microsoft YaHei", 10)).pack(anchor=W, pady=(10, 0))
        self.aes_dec_pass = ttk.Entry(dec_inner, show="•")
        self.aes_dec_pass.pack(fill=X, pady=(5, 0))
        ttk.Label(dec_inner, text="解密结果", font=("Microsoft YaHei", 10)).pack(anchor=W, pady=(10, 0))
        self.aes_dec_result = tk.Text(dec_inner, height=3, wrap=WORD, font=("Consolas", 10))
        self.aes_dec_result.pack(fill=X, pady=(5, 0))
        btn_frame2 = ttk.Frame(dec_inner)
        btn_frame2.pack(fill=X, pady=(10, 0))
        ttk.Button(btn_frame2, text="🔓 执行解密", bootstyle="info", command=self.aes_decrypt).pack(side=LEFT, padx=(0, 10))
        ttk.Button(btn_frame2, text="📋 复制结果", bootstyle="info-outline", command=self.aes_copy_dec_result).pack(side=LEFT, padx=(0, 10))
        ttk.Button(btn_frame2, text="🗑 清空", bootstyle="outline", command=self.aes_clear_decrypt).pack(side=LEFT)

        return frame

    def toggle_aes_mode(self):
        if self.aes_mode.get() == "encrypt":
            self.aes_decrypt_frame.pack_forget()
            self.aes_encrypt_frame.pack(fill=X, pady=5)
        else:
            self.aes_encrypt_frame.pack_forget()
            self.aes_decrypt_frame.pack(fill=X, pady=5)

    def build_stego_frame(self, parent):
        frame = ttk.Frame(parent)

        ttk.Label(frame, text="🖼️ 图片隐写检测", font=("Consolas", 18, "bold")).pack(anchor=W, pady=(0, 5))
        ttk.Label(frame, text="检测图片是否通过 LSB 隐藏了额外数据", font=("Microsoft YaHei", 10), foreground="#6c757d").pack(anchor=W, pady=(0, 15))

        card = ttk.Labelframe(frame, text="文件选择", bootstyle="success")
        card.pack(fill=X, pady=5)
        inner = ttk.Frame(card)
        inner.pack(fill=X, padx=15, pady=15)
        ttk.Label(inner, text="选择图片（PNG/BMP）", font=("Microsoft YaHei", 10)).pack(anchor=W)
        f = ttk.Frame(inner)
        f.pack(fill=X, pady=(5, 0))
        self.stego_file_entry = ttk.Entry(f)
        self.stego_file_entry.pack(side=LEFT, fill=X, expand=True)
        ttk.Button(f, text="浏览", bootstyle="success-outline", command=self.browse_stego_file).pack(side=LEFT, padx=(8, 0))
        ttk.Button(inner, text="🔍 开始检测", bootstyle="success", command=self.stego_detect, width=20).pack(pady=(15, 0))

        self.stego_result_frame = ttk.Labelframe(frame, text="📊 检测结果", bootstyle="success")
        self.stego_result_frame.pack(fill=X, pady=(15, 5))
        result_inner = ttk.Frame(self.stego_result_frame)
        result_inner.pack(fill=X, padx=15, pady=15)
        self.stego_result_text = tk.Text(result_inner, height=10, wrap=WORD, font=("Consolas", 10), state=DISABLED)
        self.stego_result_text.pack(fill=X)

        return frame

    def build_qr_frame(self, parent):
        frame = ttk.Frame(parent)

        ttk.Label(frame, text="📷 二维码安全解析", font=("Consolas", 18, "bold")).pack(anchor=W, pady=(0, 5))
        ttk.Label(frame, text="解析二维码内容，识别潜在风险", font=("Microsoft YaHei", 10), foreground="#6c757d").pack(anchor=W, pady=(0, 15))

        card = ttk.Labelframe(frame, text="文件/截图", bootstyle="primary")
        card.pack(fill=X, pady=5)
        inner = ttk.Frame(card)
        inner.pack(fill=X, padx=15, pady=15)
        ttk.Label(inner, text="选择图片", font=("Microsoft YaHei", 10)).pack(anchor=W)
        f = ttk.Frame(inner)
        f.pack(fill=X, pady=(5, 0))
        self.qr_file_entry = ttk.Entry(f)
        self.qr_file_entry.pack(side=LEFT, fill=X, expand=True)
        ttk.Button(f, text="浏览", bootstyle="primary-outline", command=self.browse_qr_file).pack(side=LEFT, padx=(8, 0))
        ttk.Button(inner, text="📋 从剪贴板读取", bootstyle="primary-outline", command=self.qr_from_clipboard).pack(anchor=W, pady=(10, 0))
        ttk.Button(inner, text="🔍 解析二维码", bootstyle="primary", command=self.qr_parse, width=20).pack(pady=(10, 0))

        self.qr_result_frame = ttk.Labelframe(frame, text="📊 解析结果", bootstyle="primary")
        self.qr_result_frame.pack(fill=X, pady=(15, 5))
        result_inner = ttk.Frame(self.qr_result_frame)
        result_inner.pack(fill=X, padx=15, pady=15)
        self.qr_result_text = tk.Text(result_inner, height=12, wrap=WORD, font=("Consolas", 10), state=DISABLED)
        self.qr_result_text.pack(fill=X)
        btn_frame = ttk.Frame(result_inner)
        btn_frame.pack(fill=X, pady=(10, 0))
        ttk.Button(btn_frame, text="🌐 浏览器打开", bootstyle="primary-outline", command=self.qr_open_browser).pack(side=LEFT, padx=(0, 10))
        ttk.Button(btn_frame, text="📋 复制内容", bootstyle="primary-outline", command=self.qr_copy_content).pack(side=LEFT)

        return frame

    def build_port_frame(self, parent):
        frame = ttk.Frame(parent)

        ttk.Label(frame, text="🌐 本机端口快照", font=("Consolas", 18, "bold")).pack(anchor=W, pady=(0, 5))
        ttk.Label(frame, text="扫描本机开放端口，排查异常监听", font=("Microsoft YaHei", 10), foreground="#6c757d").pack(anchor=W, pady=(0, 15))

        card = ttk.Labelframe(frame, text="扫描配置", bootstyle="secondary")
        card.pack(fill=X, pady=5)
        inner = ttk.Frame(card)
        inner.pack(fill=X, padx=15, pady=15)
        ttk.Label(inner, text="扫描范围:", font=("Microsoft YaHei", 10)).pack(side=LEFT)
        self.port_range = ttk.StringVar(value="common")
        ttk.Radiobutton(inner, text="常用端口", variable=self.port_range, value="common", bootstyle="secondary-toolbutton").pack(side=LEFT, padx=(10, 5))
        ttk.Radiobutton(inner, text="全部端口", variable=self.port_range, value="all", bootstyle="secondary-toolbutton").pack(side=LEFT, padx=5)
        ttk.Button(inner, text="🔍 开始扫描", bootstyle="secondary", command=self.port_scan).pack(side=LEFT, padx=(20, 0))

        result_card = ttk.Labelframe(frame, text="📋 开放端口列表", bootstyle="secondary")
        result_card.pack(fill=BOTH, expand=True, pady=(15, 5))
        result_inner = ttk.Frame(result_card)
        result_inner.pack(fill=BOTH, expand=True, padx=10, pady=10)

        cols = ("protocol", "local_addr", "port", "status", "process")
        self.port_tree = ttk.Treeview(result_inner, columns=cols, show="headings", height=10)
        self.port_tree.heading("protocol", text="协议")
        self.port_tree.heading("local_addr", text="本地地址")
        self.port_tree.heading("port", text="端口")
        self.port_tree.heading("status", text="状态")
        self.port_tree.heading("process", text="进程名")
        self.port_tree.column("protocol", width=60)
        self.port_tree.column("local_addr", width=120)
        self.port_tree.column("port", width=60)
        self.port_tree.column("status", width=80)
        self.port_tree.column("process", width=200)
        self.port_tree.pack(side=LEFT, fill=BOTH, expand=True)

        scrollbar = ttk.Scrollbar(result_inner, command=self.port_tree.yview)
        self.port_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=RIGHT, fill=Y)

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=X, pady=5)
        ttk.Button(btn_frame, text="📋 复制", bootstyle="outline", command=self.port_copy).pack(side=LEFT, padx=(0, 10))
        ttk.Button(btn_frame, text="📁 导出 CSV", bootstyle="outline", command=self.port_export).pack(side=LEFT, padx=(0, 10))
        ttk.Button(btn_frame, text="🔄 刷新", bootstyle="outline", command=self.port_scan).pack(side=LEFT)

        return frame

    def build_clipboard_frame(self, parent):
        frame = ttk.Frame(parent)

        ttk.Label(frame, text="🛡️ 剪贴板安全哨兵", font=("Consolas", 18, "bold")).pack(anchor=W, pady=(0, 5))
        ttk.Label(frame, text="防止敏感信息在剪贴板中残留", font=("Microsoft YaHei", 10), foreground="#6c757d").pack(anchor=W, pady=(0, 15))

        manual_card = ttk.Labelframe(frame, text="🧹 手动清理", bootstyle="info")
        manual_card.pack(fill=X, pady=5)
        manual_inner = ttk.Frame(manual_card)
        manual_inner.pack(fill=X, padx=15, pady=15)
        ttk.Label(manual_inner, text="当前剪贴板内容预览", font=("Microsoft YaHei", 10)).pack(anchor=W)
        self.clip_preview = tk.Text(manual_inner, height=3, wrap=WORD, font=("Consolas", 10), state=DISABLED)
        self.clip_preview.pack(fill=X, pady=(5, 0))
        ttk.Button(manual_inner, text="🧹 立即清空剪贴板", bootstyle="info", command=self.clipboard_clear_manual, width=20).pack(pady=(10, 0))

        auto_card = ttk.Labelframe(frame, text="⏱️ 自动清理", bootstyle="info")
        auto_card.pack(fill=X, pady=(15, 5))
        auto_inner = ttk.Frame(auto_card)
        auto_inner.pack(fill=X, padx=15, pady=15)
        self.clip_auto = tk.BooleanVar(value=False)
        ttk.Checkbutton(auto_inner, text="启用自动清理", variable=self.clip_auto, bootstyle="info-round-toggle", command=self.clipboard_toggle_auto).pack(anchor=W)

        delay_frame = ttk.Frame(auto_inner)
        delay_frame.pack(fill=X, pady=(10, 0))
        ttk.Label(delay_frame, text="自动清理延迟:", font=("Microsoft YaHei", 10)).pack(side=LEFT)
        self.clip_delay = tk.IntVar(value=30)
        ttk.Scale(delay_frame, from_=5, to=120, variable=self.clip_delay, orient=HORIZONTAL, length=200, command=self._on_clip_delay_change).pack(side=LEFT, padx=(10, 5))
        self.clip_delay_label = ttk.Label(delay_frame, text="30", font=("Consolas", 11, "bold"), foreground="#3B82F6")
        self.clip_delay_label.pack(side=LEFT)
        ttk.Label(delay_frame, text="秒", font=("Microsoft YaHei", 10)).pack(side=LEFT)

        # 启动剪贴板监控循环
        self._clipboard_monitor()

        return frame

    def build_shred_frame(self, parent):
        frame = ttk.Frame(parent)

        ttk.Label(frame, text="🗑️ 文件安全粉碎", font=("Consolas", 18, "bold")).pack(anchor=W, pady=(0, 5))
        ttk.Label(frame, text="覆写删除敏感文件，防止数据恢复", font=("Microsoft YaHei", 10), foreground="#6c757d").pack(anchor=W, pady=(0, 15))

        card = ttk.Labelframe(frame, text="⚠️ 文件选择", bootstyle="danger")
        card.pack(fill=X, pady=5)
        inner = ttk.Frame(card)
        inner.pack(fill=X, padx=15, pady=15)
        ttk.Label(inner, text="选择文件/文件夹", font=("Microsoft YaHei", 10)).pack(anchor=W)
        f = ttk.Frame(inner)
        f.pack(fill=X, pady=(5, 0))
        self.shred_path_entry = ttk.Entry(f)
        self.shred_path_entry.pack(side=LEFT, fill=X, expand=True)
        ttk.Button(f, text="浏览文件", bootstyle="danger-outline", command=self.browse_shred_file).pack(side=LEFT, padx=(8, 0))
        ttk.Button(f, text="浏览文件夹", bootstyle="danger-outline", command=self.browse_shred_dir).pack(side=LEFT, padx=(8, 0))

        self.shred_recursive = tk.BooleanVar(value=False)
        ttk.Checkbutton(inner, text="包含子文件夹", variable=self.shred_recursive, bootstyle="danger-round-toggle").pack(anchor=W, pady=(10, 0))

        ttk.Label(inner, text="覆写次数:", font=("Microsoft YaHei", 10)).pack(anchor=W, pady=(10, 0))
        passes_frame = ttk.Frame(inner)
        passes_frame.pack(fill=X, pady=(5, 0))
        self.shred_passes = ttk.IntVar(value=3)
        ttk.Radiobutton(passes_frame, text="1次（快速）", variable=self.shred_passes, value=1, bootstyle="danger-toolbutton", width=10).pack(side=LEFT, padx=(0, 10))
        ttk.Radiobutton(passes_frame, text="3次（标准）", variable=self.shred_passes, value=3, bootstyle="danger-toolbutton", width=10).pack(side=LEFT, padx=(0, 10))
        ttk.Radiobutton(passes_frame, text="7次（军规）", variable=self.shred_passes, value=7, bootstyle="danger-toolbutton", width=10).pack(side=LEFT, padx=(0, 10))

        ttk.Label(inner, text="覆写模式:", font=("Microsoft YaHei", 10)).pack(anchor=W, pady=(10, 0))
        mode_frame = ttk.Frame(inner)
        mode_frame.pack(fill=X, pady=(5, 0))
        self.shred_mode = ttk.StringVar(value="random")
        ttk.Radiobutton(mode_frame, text="随机数据", variable=self.shred_mode, value="random", bootstyle="danger-toolbutton", width=10).pack(side=LEFT, padx=(0, 10))
        ttk.Radiobutton(mode_frame, text="0x00", variable=self.shred_mode, value="zero", bootstyle="danger-toolbutton", width=10).pack(side=LEFT, padx=(0, 10))

        warn = ttk.Label(inner, text="⚠️ 警告：文件粉碎后将无法恢复，请确认选择的文件是否正确", font=("Microsoft YaHei", 9), foreground="#EF4444")
        warn.pack(anchor=W, pady=(15, 0))

        ttk.Button(inner, text="🔥 确认粉碎", bootstyle="danger", command=self.shred_execute, width=20).pack(pady=(15, 0))

        self.shred_progress = ttk.Progressbar(frame, mode="determinate", bootstyle="danger")
        self.shred_progress.pack(fill=X, pady=(15, 5))

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

        # DeepSeek AI 配置卡片
        ai_card = ttk.Labelframe(frame, text="🤖 DeepSeek AI 配置", bootstyle="info")
        ai_card.pack(fill=X, pady=5)

        ai_inner = ttk.Frame(ai_card)
        ai_inner.pack(fill=X, padx=15, pady=15)

        # API Key
        ttk.Label(ai_inner, text="API Key:").grid(row=0, column=0, sticky=W, pady=5)
        api_key_row = ttk.Frame(ai_inner)
        api_key_row.grid(row=0, column=1, sticky=EW, padx=(10, 0), pady=5)
        ai_inner.columnconfigure(1, weight=1)
        self.ai_api_key_entry = ttk.Entry(api_key_row, show="•")
        self.ai_api_key_entry.pack(side=LEFT, fill=X, expand=True)
        self.ai_api_key_visible = False
        ttk.Button(api_key_row, text="👁", bootstyle="info-outline", command=self._toggle_ai_key_visibility, width=4).pack(side=LEFT, padx=(5, 0))

        # Base URL
        ttk.Label(ai_inner, text="API 地址:").grid(row=1, column=0, sticky=W, pady=5)
        self.ai_base_url_entry = ttk.Entry(ai_inner)
        self.ai_base_url_entry.grid(row=1, column=1, sticky=EW, padx=(10, 0), pady=5)

        # 模型选择
        ttk.Label(ai_inner, text="模型:").grid(row=2, column=0, sticky=W, pady=5)
        self.ai_model_var = ttk.StringVar(value="deepseek-chat")
        ai_model_combo = ttk.Combobox(ai_inner, textvariable=self.ai_model_var, values=["deepseek-chat", "deepseek-reasoner"], state="readonly")
        ai_model_combo.grid(row=2, column=1, sticky=EW, padx=(10, 0), pady=5)

        # 温度参数
        ttk.Label(ai_inner, text="温度:").grid(row=3, column=0, sticky=W, pady=5)
        temp_frame = ttk.Frame(ai_inner)
        temp_frame.grid(row=3, column=1, sticky=EW, padx=(10, 0), pady=5)
        self.ai_temp_var = tk.DoubleVar(value=0.8)
        ttk.Scale(temp_frame, from_=0.5, to=1.0, variable=self.ai_temp_var, orient=HORIZONTAL, length=200).pack(side=LEFT)
        self.ai_temp_label = ttk.Label(temp_frame, text="0.8", font=("Consolas", 10), width=4)
        self.ai_temp_label.pack(side=LEFT, padx=(10, 0))
        self.ai_temp_var.trace_add("write", lambda *args: self.ai_temp_label.configure(text=f"{self.ai_temp_var.get():.1f}"))

        # 保存按钮
        ttk.Button(ai_inner, text="💾 保存 AI 配置", bootstyle="info", command=self._save_deepseek_config_to_file).grid(row=4, column=0, columnspan=2, pady=(10, 0), sticky=W)

        # 加载现有配置到界面
        self._apply_deepseek_config_to_ui()

        return frame

    def _load_deepseek_config(self):
        """从 config.json 加载 DeepSeek 配置"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            return config.get("deepseek", {
                "api_key": "",
                "base_url": "https://api.deepseek.com",
                "model": "deepseek-chat",
                "temperature": 0.8
            })
        except Exception:
            return {
                "api_key": "",
                "base_url": "https://api.deepseek.com",
                "model": "deepseek-chat",
                "temperature": 0.8
            }

    def _apply_deepseek_config_to_ui(self):
        """将配置应用到设置页面 UI"""
        cfg = self.deepseek_config
        self.ai_api_key_entry.delete(0, END)
        self.ai_api_key_entry.insert(0, cfg.get("api_key", ""))
        self.ai_base_url_entry.delete(0, END)
        self.ai_base_url_entry.insert(0, cfg.get("base_url", "https://api.deepseek.com"))
        self.ai_model_var.set(cfg.get("model", "deepseek-chat"))
        temp = cfg.get("temperature", 0.8)
        self.ai_temp_var.set(temp)
        self.ai_temp_label.configure(text=f"{temp:.1f}")

    def _save_deepseek_config_to_file(self):
        """保存 DeepSeek 配置到 config.json"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            config["deepseek"] = {
                "api_key": self.ai_api_key_entry.get().strip(),
                "base_url": self.ai_base_url_entry.get().strip() or "https://api.deepseek.com",
                "model": self.ai_model_var.get(),
                "temperature": round(self.ai_temp_var.get(), 1)
            }

            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=4)

            self.deepseek_config = config["deepseek"]
            messagebox.showinfo("提示", "DeepSeek AI 配置已保存")
        except Exception as e:
            messagebox.showerror("错误", f"保存配置失败: {str(e)}")

    def _toggle_ai_key_visibility(self):
        """切换 API Key 显示/隐藏"""
        self.ai_api_key_visible = not self.ai_api_key_visible
        self.ai_api_key_entry.configure(show="" if self.ai_api_key_visible else "•")

    def create_log_area(self, parent):
        self.log_frame = ttk.Labelframe(parent, text="📋 输出控制台", bootstyle="dark")
        self.log_frame.pack(fill=BOTH, expand=True, pady=(15, 5))

        text_frame = ttk.Frame(self.log_frame)
        text_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)

        self.output_text = tk.Text(text_frame, height=8, wrap=WORD, font=("Consolas", 12), state=DISABLED)
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
        self.action_bar = ttk.Frame(parent)
        self.action_bar.pack(fill=X, pady=5)

        self.run_button = ttk.Button(self.action_bar, text="▶  开始检测", bootstyle="success", command=self.run_detection, width=15)
        self.run_button.pack(side=LEFT, padx=(0, 10))

        self.stop_button = ttk.Button(self.action_bar, text="⏹  停止", bootstyle="danger", command=self.stop_detection, state=DISABLED, width=12)
        self.stop_button.pack(side=LEFT, padx=5)

        self.progress = ttk.Progressbar(self.action_bar, mode="indeterminate", bootstyle="success")
        self.progress.pack(side=LEFT, fill=X, expand=True, padx=10)

        ttk.Button(self.action_bar, text="🗑  清空日志", bootstyle="outline", command=self.clear_output).pack(side=RIGHT)

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

    def _ai_optimize_password(self):
        """调用 DeepSeek AI 优化密码"""
        user_input = self.ai_opt_input.get().strip()
        if not user_input:
            messagebox.showwarning("提示", "请输入密码风格或关键词")
            return

        api_key = self.deepseek_config.get("api_key", "")
        if not api_key:
            messagebox.showwarning("提示", "请先在设置中配置 DeepSeek API Key")
            return

        # 显示结果区域并清空旧数据
        self.ai_result_frame.pack(fill=X, pady=(10, 0))
        for var in self.ai_password_vars:
            var.set("")
        self.ai_suggestion_label.configure(text="")

        self.logger.info("正在调用 DeepSeek AI 生成密码建议...")
        thread = threading.Thread(target=self._ai_optimize_thread, args=(user_input,), daemon=True)
        thread.start()

    def _ai_optimize_thread(self, user_input):
        """在后台线程中调用 DeepSeek API"""
        try:
            client = DeepSeekClient(
                api_key=self.deepseek_config.get("api_key", ""),
                base_url=self.deepseek_config.get("base_url", "https://api.deepseek.com"),
                model=self.deepseek_config.get("model", "deepseek-chat"),
                temperature=self.deepseek_config.get("temperature", 0.8)
            )
            result = client.optimize_password(user_input)
            self.root.after(0, lambda: self._display_ai_passwords(result))
        except Exception as e:
            self.root.after(0, lambda: self._show_ai_error(str(e)))

    def _display_ai_passwords(self, result):
        """在界面上显示 AI 生成的密码"""
        passwords = result.get("passwords", [])
        for i, item in enumerate(passwords):
            if i < len(self.ai_password_vars):
                val = item.get("value", "")
                self.ai_password_vars[i].set(val)

        suggestion = result.get("suggestion", "")
        if suggestion:
            self.ai_suggestion_label.configure(text=f"💡 AI 建议：{suggestion}")

        self.logger.info(f"AI 密码优化完成，生成 {len(passwords)} 组建议密码")

    def _show_ai_error(self, error_msg):
        """显示 AI 调用错误"""
        self.logger.error(f"AI 调用失败: {error_msg}")
        messagebox.showerror("AI 调用失败", error_msg)

    def _copy_ai_password(self, var):
        """复制 AI 生成的密码到剪贴板"""
        password = var.get()
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

    # ========== PDF 加解密 ==========
    def browse_pdf_file(self):
        filename = filedialog.askopenfilename(title="选择 PDF 文件", filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")])
        if filename:
            self.pdf_file_entry.delete(0, END)
            self.pdf_file_entry.insert(0, filename)

    def browse_pdf_decrypt_file(self):
        filename = filedialog.askopenfilename(title="选择 PDF 文件", filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")])
        if filename:
            self.pdf_decrypt_file_entry.delete(0, END)
            self.pdf_decrypt_file_entry.insert(0, filename)

    def _resolve_pdf_outfile(self, infile, outfile, suffix="_out.pdf"):
        """解析输出文件路径：无路径时用原文件夹，无.pdf后缀时自动添加"""
        if not outfile:
            return infile.replace(".pdf", suffix)
        # 仅输入文件名时，使用原文件所在目录
        if not os.path.dirname(outfile):
            outfile = os.path.join(os.path.dirname(infile), outfile)
        # 自动补全 .pdf 后缀
        if not outfile.lower().endswith(".pdf"):
            outfile += ".pdf"
        return outfile

    def pdf_process(self):
        infile = self.pdf_file_entry.get()
        if not infile or not os.path.exists(infile):
            messagebox.showwarning("提示", "请选择有效的 PDF 文件")
            return
        outfile = self.pdf_out_entry.get()
        outfile = self._resolve_pdf_outfile(infile, outfile, "_encrypted.pdf")
        thread = threading.Thread(target=self._pdf_encrypt_thread, args=(infile, outfile), daemon=True)
        thread.start()

    def _pdf_encrypt_thread(self, infile, outfile):
        try:
            self.logger.info(f"开始加密 PDF: {os.path.basename(infile)}")
            reader = PdfReader(infile)
            writer = PdfWriter()
            for page in reader.pages:
                writer.add_page(page)
            open_pass = self.pdf_open_pass.get()
            perm_pass = self.pdf_perm_pass.get()
            # 若用户未输入密码，使用默认空密码，保证界面上"可选"提示有效
            if not open_pass and not perm_pass:
                open_pass = ""
            kwargs = {
                "user_password": open_pass if open_pass else "",
            }
            if perm_pass:
                kwargs["owner_password"] = perm_pass
            # 通过 permissions_flag 控制权限（pypdf 无 add_prohibition 方法）
            permissions_flag = -4  # 默认允许所有权限
            if self.pdf_no_print.get():
                permissions_flag &= ~UserAccessPermissions.PRINT.value
            if self.pdf_no_copy.get():
                permissions_flag &= ~UserAccessPermissions.EXTRACT.value
            if self.pdf_no_edit.get():
                permissions_flag &= ~UserAccessPermissions.MODIFY.value
            kwargs["permissions_flag"] = permissions_flag
            writer.encrypt(**kwargs)
            with open(outfile, "wb") as f:
                writer.write(f)
            self.logger.info(f"加密完成，已保存至: {os.path.abspath(outfile)}")
            self.root.after(0, lambda: os.startfile(os.path.dirname(os.path.abspath(outfile))))
        except Exception as e:
            self.logger.error(f"PDF 加密失败: {str(e)}")

    def pdf_decrypt_process(self):
        infile = self.pdf_decrypt_file_entry.get()
        if not infile or not os.path.exists(infile):
            messagebox.showwarning("提示", "请选择有效的 PDF 文件")
            return
        outfile = self.pdf_decrypt_out_entry.get()
        outfile = self._resolve_pdf_outfile(infile, outfile, "_decrypted.pdf")
        thread = threading.Thread(target=self._pdf_decrypt_thread, args=(infile, outfile), daemon=True)
        thread.start()

    def _pdf_decrypt_thread(self, infile, outfile):
        try:
            self.logger.info(f"开始解密 PDF: {os.path.basename(infile)}")
            reader = PdfReader(infile)
            password = self.pdf_decrypt_pass.get()
            if reader.is_encrypted and password:
                reader.decrypt(password)
            writer = PdfWriter()
            for page in reader.pages:
                writer.add_page(page)
            with open(outfile, "wb") as f:
                writer.write(f)
            self.logger.info(f"解密完成，已保存至: {os.path.abspath(outfile)}")
            self.root.after(0, lambda: os.startfile(os.path.dirname(os.path.abspath(outfile))))
        except Exception as e:
            self.logger.error(f"PDF 解密失败: {str(e)}")

    # ========== AES 文本加解密 ==========
    def _derive_key(self, password: str, salt: bytes = None):
        if salt is None:
            salt = os.urandom(16)
        kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=100000)
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key, salt

    def aes_encrypt(self):
        plain = self.aes_plain_text.get("1.0", END).strip()
        password = self.aes_enc_pass.get()
        if not plain:
            messagebox.showwarning("提示", "请输入待加密文本")
            return
        if not password:
            messagebox.showwarning("提示", "请输入密码")
            return
        try:
            key, salt = self._derive_key(password)
            f = Fernet(key)
            token = f.encrypt(plain.encode())
            result = base64.b64encode(salt + token).decode()
            self.aes_enc_result.delete("1.0", END)
            self.aes_enc_result.insert("1.0", result)
            self.logger.info("文本加密完成")
        except Exception as e:
            self.logger.error(f"加密失败: {str(e)}")

    def aes_decrypt(self):
        cipher = self.aes_cipher_text.get("1.0", END).strip()
        password = self.aes_dec_pass.get()
        if not cipher:
            messagebox.showwarning("提示", "请输入待解密文本")
            return
        if not password:
            messagebox.showwarning("提示", "请输入密码")
            return
        try:
            data = base64.b64decode(cipher.encode())
            salt = data[:16]
            token = data[16:]
            key, _ = self._derive_key(password, salt)
            f = Fernet(key)
            plain = f.decrypt(token).decode()
            self.aes_dec_result.delete("1.0", END)
            self.aes_dec_result.insert("1.0", plain)
            self.logger.info("文本解密完成")
        except Exception:
            messagebox.showerror("错误", "解密失败，请检查密码或密文格式")

    def aes_copy_enc_result(self):
        text = self.aes_enc_result.get("1.0", END).strip()
        if text:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.root.update()
            self.logger.info("加密结果已复制到剪贴板")

    def aes_copy_dec_result(self):
        text = self.aes_dec_result.get("1.0", END).strip()
        if text:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.root.update()
            self.logger.info("解密结果已复制到剪贴板")

    def aes_clear_encrypt(self):
        self.aes_plain_text.delete("1.0", END)
        self.aes_enc_pass.delete(0, END)
        self.aes_enc_result.delete("1.0", END)

    def aes_clear_decrypt(self):
        self.aes_cipher_text.delete("1.0", END)
        self.aes_dec_pass.delete(0, END)
        self.aes_dec_result.delete("1.0", END)

    # ========== 图片隐写检测 ==========
    def browse_stego_file(self):
        filename = filedialog.askopenfilename(title="选择图片", filetypes=[("Image files", "*.png *.bmp"), ("All files", "*.*")])
        if filename:
            self.stego_file_entry.delete(0, END)
            self.stego_file_entry.insert(0, filename)

    def stego_detect(self):
        filepath = self.stego_file_entry.get()
        if not filepath or not os.path.exists(filepath):
            messagebox.showwarning("提示", "请选择有效的图片文件")
            return
        thread = threading.Thread(target=self._stego_detect_thread, args=(filepath,), daemon=True)
        thread.start()

    def _stego_detect_thread(self, filepath):
        try:
            self.logger.info(f"开始检测图片: {os.path.basename(filepath)}")
            img = Image.open(filepath)
            if img.mode not in ("RGB", "RGBA", "L"):
                self.logger.warning("仅支持 RGB/RGBA/灰度图片")
                return
            pixels = list(img.getdata())
            result_lines = [f"文件: {os.path.basename(filepath)}", f"尺寸: {img.size[0]} x {img.size[1]}", f"模式: {img.mode}", ""]
            result_lines.append("── LSB 熵值分析 ──")

            channels = []
            if img.mode == "RGB":
                channels = [("R", 0), ("G", 1), ("B", 2)]
            elif img.mode == "RGBA":
                channels = [("R", 0), ("G", 1), ("B", 2), ("A", 3)]
            elif img.mode == "L":
                channels = [("L", 0)]

            has_anomaly = False
            for name, idx in channels:
                bits = [str(p[idx] & 1) for p in pixels if isinstance(p, (tuple, list)) and len(p) > idx]
                if not bits:
                    continue
                entropy = self._calc_entropy(bits)
                status = "正常"
                if entropy > 7.5:
                    status = "异常🔴"
                    has_anomaly = True
                elif entropy > 6.0:
                    status = "可疑🟡"
                result_lines.append(f"{name} 通道熵值: {entropy:.2f}  [{status}]")

            result_lines.append("")
            if has_anomaly:
                result_lines.append("判定结果: 疑似隐藏数据")
                result_lines.append("建议: 使用专业工具深入分析")
            else:
                result_lines.append("判定结果: 未发现明显隐写痕迹")

            def update():
                self.stego_result_text.configure(state=NORMAL)
                self.stego_result_text.delete("1.0", END)
                self.stego_result_text.insert("1.0", "\n".join(result_lines))
                self.stego_result_text.configure(state=DISABLED)

            self.root.after(0, update)
            self.logger.info("图片隐写检测完成")
        except Exception as e:
            self.logger.error(f"检测失败: {str(e)}")

    def _calc_entropy(self, bits):
        from collections import Counter
        n = len(bits)
        if n == 0:
            return 0.0
        counts = Counter(bits)
        entropy = 0.0
        for count in counts.values():
            p = count / n
            if p > 0:
                entropy -= p * math.log2(p)
        return entropy

    # ========== 二维码解析 ==========
    def browse_qr_file(self):
        filename = filedialog.askopenfilename(title="选择图片", filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp"), ("All files", "*.*")])
        if filename:
            self.qr_file_entry.delete(0, END)
            self.qr_file_entry.insert(0, filename)

    def qr_from_clipboard(self):
        try:
            img = ImageGrab.grabclipboard()
            if img is None:
                messagebox.showwarning("提示", "剪贴板中没有图片")
                return
            temp_path = os.path.join(os.path.expanduser("~"), "temp_qr.png")
            img.save(temp_path)
            self.qr_file_entry.delete(0, END)
            self.qr_file_entry.insert(0, temp_path)
            self.logger.info("已从剪贴板读取图片")
        except Exception as e:
            self.logger.error(f"读取剪贴板失败: {str(e)}")

    def qr_parse(self):
        filepath = self.qr_file_entry.get()
        if not filepath or not os.path.exists(filepath):
            messagebox.showwarning("提示", "请选择有效的图片文件")
            return
        thread = threading.Thread(target=self._qr_parse_thread, args=(filepath,), daemon=True)
        thread.start()

    def _qr_parse_thread(self, filepath):
        try:
            self.logger.info(f"开始解析二维码: {os.path.basename(filepath)}")
            img = cv2.imread(filepath)
            results = decode(img)
            if not results:
                def no_result():
                    self.qr_result_text.configure(state=NORMAL)
                    self.qr_result_text.delete("1.0", END)
                    self.qr_result_text.insert("1.0", "未检测到二维码")
                    self.qr_result_text.configure(state=DISABLED)
                self.root.after(0, no_result)
                self.logger.info("未检测到二维码")
                return

            lines = []
            for r in results:
                data = r.data.decode("utf-8", errors="replace")
                lines.append(f"类型: {r.type}")
                lines.append(f"内容: {data}")
                lines.append("")
                if data.startswith("http://") or data.startswith("https://"):
                    lines.append("── 安全检测 ──")
                    real_url = self._follow_url(data)
                    domain = urlparse(real_url).netloc
                    lines.append(f"真实目标: {real_url}")
                    lines.append(f"域名: {domain}")
                    risk = self._check_domain_risk(domain, real_url)
                    lines.append(f"风险等级: {risk}")
                    if "危险" in risk or "可疑" in risk:
                        lines.append("⚠️ 警告: 该链接存在安全风险，建议不要访问")
                lines.append("─" * 40)

            def update():
                self.qr_result_text.configure(state=NORMAL)
                self.qr_result_text.delete("1.0", END)
                self.qr_result_text.insert("1.0", "\n".join(lines))
                self.qr_result_text.configure(state=DISABLED)

            self.root.after(0, update)
            self.logger.info("二维码解析完成")
        except Exception as e:
            self.logger.error(f"解析失败: {str(e)}")

    def _follow_url(self, url, depth=0):
        if depth > 3:
            return url
        try:
            import requests
            resp = requests.head(url, allow_redirects=True, timeout=5)
            return resp.url
        except Exception:
            return url

    def _check_domain_risk(self, domain, url):
        shorteners = ["t.cn", "bit.ly", "tinyurl.com", "goo.gl", "short.url", "dwz.cn", "is.gd"]
        if any(s in domain for s in shorteners):
            return "⚠️ 可疑（短链接服务）"
        suspicious = ["login", "verify", "secure", "account", "update", "confirm"]
        if any(s in domain.lower() for s in suspicious):
            return "⚠️ 可疑（域名含敏感词）"
        if "https" not in url:
            return "🟡 低危（非 HTTPS）"
        return "🟢 正常"

    def qr_open_browser(self):
        text = self.qr_result_text.get("1.0", END)
        import re
        urls = re.findall(r"https?://[^\s]+", text)
        if urls:
            import webbrowser
            webbrowser.open(urls[0])
        else:
            messagebox.showwarning("提示", "未找到可打开的链接")

    def qr_copy_content(self):
        text = self.qr_result_text.get("1.0", END).strip()
        if text:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.root.update()
            self.logger.info("解析结果已复制到剪贴板")

    # ========== 端口快照 ==========
    def port_scan(self):
        thread = threading.Thread(target=self._port_scan_thread, daemon=True)
        thread.start()

    def _port_scan_thread(self):
        try:
            self.logger.info("开始扫描本机端口...")
            for item in self.port_tree.get_children():
                self.port_tree.delete(item)

            HIGH_RISK_PORTS = {135, 139, 445, 3389, 1433, 3306, 5432, 6379, 27017}
            conns = psutil.net_connections(kind="inet")
            seen = set()

            for conn in conns:
                if conn.status == "LISTEN" and conn.laddr:
                    key = (conn.type.name, conn.laddr.ip, conn.laddr.port)
                    if key in seen:
                        continue
                    seen.add(key)
                    proc_name = ""
                    try:
                        if conn.pid:
                            proc_name = psutil.Process(conn.pid).name()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        proc_name = "N/A"
                    tag = ""
                    if conn.laddr.port in HIGH_RISK_PORTS:
                        tag = "risk"
                    self.port_tree.insert("", END, values=(conn.type.name, conn.laddr.ip, conn.laddr.port, conn.status, proc_name), tags=(tag,))

            self.port_tree.tag_configure("risk", foreground="#EF4444")
            self.logger.info(f"扫描完成，发现 {len(seen)} 个监听端口")
        except Exception as e:
            self.logger.error(f"端口扫描失败: {str(e)}")

    def port_copy(self):
        lines = []
        for item in self.port_tree.get_children():
            vals = self.port_tree.item(item, "values")
            lines.append("\t".join(str(v) for v in vals))
        text = "\n".join(lines)
        if text:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.root.update()
            self.logger.info("端口列表已复制到剪贴板")

    def port_export(self):
        filename = filedialog.asksaveasfilename(title="导出 CSV", defaultextension=".csv", filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if not filename:
            return
        try:
            import csv
            with open(filename, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["协议", "本地地址", "端口", "状态", "进程名"])
                for item in self.port_tree.get_children():
                    writer.writerow(self.port_tree.item(item, "values"))
            self.logger.info(f"已导出至: {filename}")
        except Exception as e:
            self.logger.error(f"导出失败: {str(e)}")

    # ========== 剪贴板哨兵 ==========
    def clipboard_clear_manual(self):
        try:
            if ctypes.windll.user32.OpenClipboard(0):
                ctypes.windll.user32.EmptyClipboard()
                ctypes.windll.user32.CloseClipboard()
                self.clip_preview.configure(state=NORMAL)
                self.clip_preview.delete("1.0", END)
                self.clip_preview.insert("1.0", "[已清空]")
                self.clip_preview.configure(state=DISABLED)
                self.logger.info("剪贴板已清空")
        except Exception as e:
            self.logger.error(f"清空剪贴板失败: {str(e)}")

    def _on_clip_delay_change(self, value):
        self.clip_delay_label.configure(text=f"{int(float(value))}")

    def clipboard_toggle_auto(self):
        if self.clip_auto.get():
            self.logger.info(f"自动清理已启用，延迟 {self.clip_delay.get()} 秒")
        else:
            self.logger.info("自动清理已禁用")

    def _clipboard_monitor(self):
        try:
            text = pyperclip.paste()
            if text and text != getattr(self, "_last_clipboard", ""):
                self._last_clipboard = text
                self._clip_timestamp = time.time()
                preview = text[:200] + "..." if len(text) > 200 else text
                self.clip_preview.configure(state=NORMAL)
                self.clip_preview.delete("1.0", END)
                self.clip_preview.insert("1.0", preview)
                self.clip_preview.configure(state=DISABLED)
            elif text and self.clip_auto.get() and hasattr(self, "_clip_timestamp"):
                elapsed = time.time() - self._clip_timestamp
                if elapsed >= self.clip_delay.get():
                    self.clipboard_clear_manual()
                    self._clip_timestamp = time.time()
        except Exception:
            pass
        self.root.after(1000, self._clipboard_monitor)

    # ========== 文件粉碎 ==========
    def browse_shred_file(self):
        filename = filedialog.askopenfilename(title="选择文件")
        if filename:
            self.shred_path_entry.delete(0, END)
            self.shred_path_entry.insert(0, filename)

    def browse_shred_dir(self):
        dirname = filedialog.askdirectory(title="选择文件夹")
        if dirname:
            self.shred_path_entry.delete(0, END)
            self.shred_path_entry.insert(0, dirname)

    def shred_execute(self):
        path = self.shred_path_entry.get()
        if not path or not os.path.exists(path):
            messagebox.showwarning("提示", "请选择有效的文件或文件夹")
            return
        if not messagebox.askyesno("确认", "文件粉碎后将无法恢复，确定继续吗？"):
            return
        thread = threading.Thread(target=self._shred_thread, args=(path,), daemon=True)
        thread.start()

    def _shred_thread(self, path):
        try:
            files = []
            if os.path.isfile(path):
                files = [path]
            elif os.path.isdir(path):
                for root, dirs, filenames in os.walk(path):
                    for fn in filenames:
                        files.append(os.path.join(root, fn))
                    if not self.shred_recursive.get():
                        break

            total = len(files)
            self.logger.info(f"待处理文件数: {total}")
            for f in files:
                self.logger.info(f"  - {f}")

            # 进度条更新必须在主线程执行
            self.root.after(0, lambda: self.shred_progress.configure(maximum=total, value=0))

            for i, filepath in enumerate(files, 1):
                self._shred_file(filepath)
                self.root.after(0, lambda v=i: self.shred_progress.configure(value=v))

            if os.path.isdir(path) and self.shred_recursive.get():
                import shutil
                shutil.rmtree(path, ignore_errors=True)
                self.logger.info(f"已删除文件夹: {path}")

            self.logger.info(f"粉碎完成，共处理 {total} 个文件")
        except Exception as e:
            self.logger.error(f"粉碎失败: {str(e)}")

    def _shred_file(self, filepath):
        try:
            if not os.path.exists(filepath):
                self.logger.warning(f"文件不存在，跳过: {filepath}")
                return
            self.logger.info(f"正在删除: {filepath}")
            os.remove(filepath)
            if os.path.exists(filepath):
                self.logger.error(f"删除后文件仍存在: {filepath}")
            else:
                self.logger.info(f"删除成功: {os.path.basename(filepath)}")
        except PermissionError as e:
            self.logger.error(f"删除失败（文件被占用或无权限）: {filepath} - {e}")
        except Exception as e:
            self.logger.error(f"删除失败: {filepath} - {e}")


def main():
    root = ttk.Window(themename="darkly")
    app = LeakGuardGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
