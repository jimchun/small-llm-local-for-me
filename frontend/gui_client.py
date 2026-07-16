"""PyQt6 桌面客户端 - 零幻觉知识助手 v14"""
import sys
import requests
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QComboBox, QSpinBox,
    QGroupBox, QMessageBox, QProgressBar, QFileDialog, QCheckBox,
    QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QTextCursor


API_BASE_URL = "http://localhost:9820"


class QueryWorker(QThread):
    """后台查询线程"""
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    
    def __init__(self, question: str, use_vector: bool, top_k: int):
        super().__init__()
        self.question = question
        self.use_vector = use_vector
        self.top_k = top_k
    
    def run(self):
        try:
            response = requests.post(
                f"{API_BASE_URL}/api/query",
                json={
                    "question": self.question,
                    "use_vector_store": self.use_vector,
                    "top_k": self.top_k
                },
                timeout=60
            )
            
            if response.status_code == 200:
                self.finished.emit(response.json())
            else:
                self.error.emit(f"API 返回错误: {response.status_code}")
                
        except Exception as e:
            self.error.emit(str(e))


class FolderScanWorker(QThread):
    """文件夹扫描线程"""
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    
    def __init__(self, folder_path: str, file_types: list, recursive: bool):
        super().__init__()
        self.folder_path = folder_path
        self.file_types = file_types
        self.recursive = recursive
    
    def run(self):
        try:
            response = requests.post(
                f"{API_BASE_URL}/api/folder/scan",
                json={
                    "folder_path": self.folder_path,
                    "file_types": self.file_types,
                    "recursive": self.recursive
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("status") == "success":
                    self.finished.emit(result.get("data", {}))
                else:
                    self.error.emit(f"扫描失败: {result.get('message', '未知错误')}")
            else:
                self.error.emit(f"API 返回错误: {response.status_code} - {response.text}")
                
        except Exception as e:
            self.error.emit(str(e))


class FolderImportWorker(QThread):
    """文件夹导入线程"""
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    
    def __init__(self, folder_path: str, file_types: list, recursive: bool):
        super().__init__()
        self.folder_path = folder_path
        self.file_types = file_types
        self.recursive = recursive
    
    def run(self):
        try:
            response = requests.post(
                f"{API_BASE_URL}/api/folder/import",
                json={
                    "folder_path": self.folder_path,
                    "file_types": self.file_types,
                    "recursive": self.recursive
                },
                timeout=300  # 导入可能耗时较长
            )
            
            if response.status_code == 200:
                self.finished.emit(response.json())
            else:
                self.error.emit(f"API 返回错误: {response.status_code} - {response.text}")
                
        except Exception as e:
            self.error.emit(str(e))


class MainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Little LLM - 零幻觉知识助手 v14")
        self.setMinimumSize(1000, 700)
        self.current_worker = None
        self.folder_worker = None
        self.scanned_files = []  # 存储扫描结果
        
        self.init_ui()
    
    def init_ui(self):
        """初始化界面"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # 标题
        title_label = QLabel("🤖 Little LLM - 零幻觉知识助手")
        title_label.setFont(QFont("Microsoft YaHei", 18, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)
        
        # 副标题
        subtitle_label = QLabel("本地推理核 + 联网权威知识库 · 所有回答均来自权威数据源")
        subtitle_label.setFont(QFont("Microsoft YaHei", 10))
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_label.setStyleSheet("color: #666;")
        main_layout.addWidget(subtitle_label)
        
        # 标签页
        self.tab_widget = QTabWidget()
        self.tab_widget.setFont(QFont("Microsoft YaHei", 11))
        
        # 查询标签页
        self.query_tab = self.create_query_tab()
        self.tab_widget.addTab(self.query_tab, "🔍 智能问答")
        
        # 文件夹导入标签页
        self.import_tab = self.create_import_tab()
        self.tab_widget.addTab(self.import_tab, "📁 导入文件夹")
        
        main_layout.addWidget(self.tab_widget, 1)
        
        # 状态栏
        self.status_label = QLabel("就绪")
        self.status_label.setFont(QFont("Microsoft YaHei", 9))
        self.status_label.setStyleSheet("color: #666; padding: 5px;")
        main_layout.addWidget(self.status_label)
    
    def create_query_tab(self):
        """创建查询标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        
        # 输入区域
        input_group = QGroupBox("提问")
        input_layout = QVBoxLayout()
        
        # 问题输入框
        self.question_input = QLineEdit()
        self.question_input.setPlaceholderText("请输入您的问题，例如：量子力学是什么？")
        self.question_input.setFont(QFont("Microsoft YaHei", 11))
        self.question_input.setMinimumHeight(40)
        self.question_input.returnPressed.connect(self.on_query)
        input_layout.addWidget(self.question_input)
        
        # 配置行
        config_layout = QHBoxLayout()
        
        # 知识源选择
        config_layout.addWidget(QLabel("知识源:"))
        self.source_combo = QComboBox()
        self.source_combo.addItem("维基百科（联网）", False)
        self.source_combo.addItem("本地向量库", True)
        self.source_combo.setFont(QFont("Microsoft YaHei", 10))
        config_layout.addWidget(self.source_combo)
        
        # 检索数量
        config_layout.addWidget(QLabel("检索数量:"))
        self.top_k_spin = QSpinBox()
        self.top_k_spin.setRange(1, 10)
        self.top_k_spin.setValue(3)
        self.top_k_spin.setFont(QFont("Microsoft YaHei", 10))
        config_layout.addWidget(self.top_k_spin)
        
        config_layout.addStretch()
        
        # 查询按钮
        self.query_btn = QPushButton("🔍 查询")
        self.query_btn.setFont(QFont("Microsoft YaHei", 11, QFont.Weight.Bold))
        self.query_btn.setMinimumWidth(120)
        self.query_btn.setMinimumHeight(40)
        self.query_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
            }
            QPushButton:hover {
                background-color: #1d4ed8;
            }
            QPushButton:disabled {
                background-color: #94a3b8;
            }
        """)
        self.query_btn.clicked.connect(self.on_query)
        config_layout.addWidget(self.query_btn)
        
        input_layout.addLayout(config_layout)
        input_group.setLayout(input_layout)
        layout.addWidget(input_group)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 0)  # 无限进度
        layout.addWidget(self.progress_bar)
        
        # 结果显示区域
        result_layout = QHBoxLayout()
        
        # 左侧：回答
        answer_group = QGroupBox("回答")
        answer_layout = QVBoxLayout()
        self.answer_text = QTextEdit()
        self.answer_text.setReadOnly(True)
        self.answer_text.setFont(QFont("Microsoft YaHei", 11))
        self.answer_text.setPlaceholderText("回答将显示在这里...")
        answer_layout.addWidget(self.answer_text)
        answer_group.setLayout(answer_layout)
        result_layout.addWidget(answer_group, 2)
        
        # 右侧：引用来源
        source_group = QGroupBox("引用来源")
        source_layout = QVBoxLayout()
        self.source_text = QTextEdit()
        self.source_text.setReadOnly(True)
        self.source_text.setFont(QFont("Microsoft YaHei", 9))
        self.source_text.setPlaceholderText("引用来源将显示在这里...")
        source_layout.addWidget(self.source_text)
        source_group.setLayout(source_layout)
        result_layout.addWidget(source_group, 1)
        
        layout.addLayout(result_layout, 1)
        
        return widget
    
    def create_import_tab(self):
        """创建文件夹导入标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        
        # 文件夹选择区域
        folder_group = QGroupBox("选择文件夹")
        folder_layout = QVBoxLayout()
        
        # 路径输入行
        path_layout = QHBoxLayout()
        path_layout.addWidget(QLabel("文件夹路径:"))
        
        self.folder_path_input = QLineEdit()
        self.folder_path_input.setPlaceholderText("请选择或输入要导入的文件夹路径...")
        self.folder_path_input.setFont(QFont("Microsoft YaHei", 10))
        self.folder_path_input.setMinimumHeight(35)
        path_layout.addWidget(self.folder_path_input)
        
        self.browse_btn = QPushButton("📂 浏览")
        self.browse_btn.setFont(QFont("Microsoft YaHei", 10))
        self.browse_btn.setMinimumHeight(35)
        self.browse_btn.setMinimumWidth(80)
        self.browse_btn.clicked.connect(self.on_browse_folder)
        path_layout.addWidget(self.browse_btn)
        
        folder_layout.addLayout(path_layout)
        
        # 文件类型选择
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("文件类型:"))
        
        self.chk_txt = QCheckBox(".txt")
        self.chk_txt.setChecked(True)
        self.chk_md = QCheckBox(".md")
        self.chk_md.setChecked(True)
        self.chk_pdf = QCheckBox(".pdf")
        self.chk_pdf.setChecked(True)
        self.chk_docx = QCheckBox(".docx")
        self.chk_docx.setChecked(True)
        
        type_layout.addWidget(self.chk_txt)
        type_layout.addWidget(self.chk_md)
        type_layout.addWidget(self.chk_pdf)
        type_layout.addWidget(self.chk_docx)
        type_layout.addStretch()
        
        # 递归选项
        self.chk_recursive = QCheckBox("递归子文件夹")
        self.chk_recursive.setChecked(True)
        type_layout.addWidget(self.chk_recursive)
        
        folder_layout.addLayout(type_layout)
        
        # 操作按钮行
        btn_layout = QHBoxLayout()
        
        self.scan_btn = QPushButton("🔍 扫描文件")
        self.scan_btn.setFont(QFont("Microsoft YaHei", 11, QFont.Weight.Bold))
        self.scan_btn.setMinimumHeight(40)
        self.scan_btn.setMinimumWidth(140)
        self.scan_btn.setStyleSheet("""
            QPushButton {
                background-color: #16a34a;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
            }
            QPushButton:hover {
                background-color: #15803d;
            }
            QPushButton:disabled {
                background-color: #94a3b8;
            }
        """)
        self.scan_btn.clicked.connect(self.on_scan_folder)
        btn_layout.addWidget(self.scan_btn)
        
        self.import_btn = QPushButton("📥 导入到向量库")
        self.import_btn.setFont(QFont("Microsoft YaHei", 11, QFont.Weight.Bold))
        self.import_btn.setMinimumHeight(40)
        self.import_btn.setMinimumWidth(160)
        self.import_btn.setEnabled(False)
        self.import_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
            }
            QPushButton:hover {
                background-color: #1d4ed8;
            }
            QPushButton:disabled {
                background-color: #94a3b8;
            }
        """)
        self.import_btn.clicked.connect(self.on_import_folder)
        btn_layout.addWidget(self.import_btn)
        
        btn_layout.addStretch()
        folder_layout.addLayout(btn_layout)
        
        folder_group.setLayout(folder_layout)
        layout.addWidget(folder_group)
        
        # 导入进度条
        self.import_progress = QProgressBar()
        self.import_progress.setVisible(False)
        self.import_progress.setRange(0, 0)
        layout.addWidget(self.import_progress)
        
        # 扫描结果表格
        result_group = QGroupBox("扫描结果")
        result_layout = QVBoxLayout()
        
        # 统计信息
        self.scan_info_label = QLabel("请选择文件夹并点击「扫描文件」查看文件列表")
        self.scan_info_label.setFont(QFont("Microsoft YaHei", 10))
        self.scan_info_label.setStyleSheet("color: #666; padding: 5px;")
        result_layout.addWidget(self.scan_info_label)
        
        # 文件列表表格
        self.file_table = QTableWidget()
        self.file_table.setColumnCount(3)
        self.file_table.setHorizontalHeaderLabels(["文件名", "大小", "路径"])
        self.file_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.file_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.file_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.file_table.setColumnWidth(0, 250)
        self.file_table.setFont(QFont("Microsoft YaHei", 9))
        self.file_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.file_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.file_table.setAlternatingRowColors(True)
        result_layout.addWidget(self.file_table)
        
        result_group.setLayout(result_layout)
        layout.addWidget(result_group, 1)
        
        return widget
    
    # ========== 查询功能 ==========
    def on_query(self):
        """执行查询"""
        question = self.question_input.text().strip()
        if not question:
            QMessageBox.warning(self, "警告", "请输入问题")
            return
        
        # 禁用按钮，显示进度
        self.query_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.answer_text.clear()
        self.source_text.clear()
        self.status_label.setText("正在查询...")
        
        # 获取配置
        use_vector = self.source_combo.currentData()
        top_k = self.top_k_spin.value()
        
        # 启动后台线程
        self.current_worker = QueryWorker(question, use_vector, top_k)
        self.current_worker.finished.connect(self.on_query_finished)
        self.current_worker.error.connect(self.on_query_error)
        self.current_worker.start()
    
    def on_query_finished(self, result: dict):
        """查询完成"""
        self.query_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        # 显示回答
        answer = result.get('answer', '无回答')
        self.answer_text.setText(answer)
        
        # 显示引用来源
        sources = result.get('sources', [])
        if sources:
            source_html = "<html><body style='font-family: Microsoft YaHei;'>"
            for src in sources:
                source_html += f"""
                <div style='margin-bottom: 15px; padding: 10px; background: #f5f5f5; border-left: 3px solid #2563eb;'>
                    <div style='font-weight: bold; color: #2563eb;'>[{src.get('index')}] {src.get('title', '未知')}</div>
                    <div style='margin-top: 5px; color: #333;'>{src.get('content', '')}</div>
                    <div style='margin-top: 5px;'>
                        <a href='{src.get('url', '')}' style='color: #2563eb; text-decoration: none;'>
                            🔗 查看原文
                        </a>
                        <span style='color: #999; margin-left: 10px;'>来源: {src.get('source', '未知')}</span>
                    </div>
                </div>
                """
            source_html += "</body></html>"
            self.source_text.setHtml(source_html)
        else:
            self.source_text.setText("未找到相关来源")
        
        # 更新状态
        model = result.get('model', 'unknown')
        context_used = result.get('context_used', 0)
        self.status_label.setText(f"查询完成 | 模型: {model} | 使用 {context_used} 个上下文")
    
    def on_query_error(self, error_msg: str):
        """查询错误"""
        self.query_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"查询失败: {error_msg}")
        QMessageBox.critical(self, "错误", f"查询失败:\n{error_msg}")
    
    # ========== 文件夹导入功能 ==========
    def on_browse_folder(self):
        """浏览选择文件夹"""
        folder = QFileDialog.getExistingDirectory(self, "选择要导入的文件夹")
        if folder:
            self.folder_path_input.setText(folder)
    
    def get_selected_file_types(self) -> list:
        """获取选中的文件类型"""
        file_types = []
        if self.chk_txt.isChecked():
            file_types.append(".txt")
        if self.chk_md.isChecked():
            file_types.append(".md")
        if self.chk_pdf.isChecked():
            file_types.append(".pdf")
        if self.chk_docx.isChecked():
            file_types.append(".docx")
        return file_types
    
    def on_scan_folder(self):
        """扫描文件夹"""
        folder_path = self.folder_path_input.text().strip()
        if not folder_path:
            QMessageBox.warning(self, "警告", "请先选择文件夹路径")
            return
        
        file_types = self.get_selected_file_types()
        if not file_types:
            QMessageBox.warning(self, "警告", "请至少选择一种文件类型")
            return
        
        # 禁用按钮，显示进度
        self.scan_btn.setEnabled(False)
        self.import_progress.setVisible(True)
        self.status_label.setText(f"正在扫描: {folder_path}")
        
        # 启动扫描线程
        self.folder_worker = FolderScanWorker(
            folder_path, file_types, self.chk_recursive.isChecked()
        )
        self.folder_worker.finished.connect(self.on_scan_finished)
        self.folder_worker.error.connect(self.on_scan_error)
        self.folder_worker.start()
    
    def on_scan_finished(self, result: dict):
        """扫描完成"""
        self.scan_btn.setEnabled(True)
        self.import_progress.setVisible(False)
        
        total_files = result.get("total_files", 0)
        total_size_human = result.get("total_size_human", "0 KB")
        folder_path = result.get("folder_path", "")
        files = result.get("files", [])
        
        self.scanned_files = files
        
        # 更新统计信息
        self.scan_info_label.setText(
            f"📊 共找到 {total_files} 个文件，总大小: {total_size_human} | 路径: {folder_path}"
        )
        
        # 更新表格
        self.file_table.setRowCount(len(files))
        for i, file_info in enumerate(files):
            name_item = QTableWidgetItem(file_info.get("name", ""))
            size_item = QTableWidgetItem(file_info.get("size_human", ""))
            path_item = QTableWidgetItem(file_info.get("path", ""))
            
            self.file_table.setItem(i, 0, name_item)
            self.file_table.setItem(i, 1, size_item)
            self.file_table.setItem(i, 2, path_item)
        
        # 启用导入按钮
        if total_files > 0:
            self.import_btn.setEnabled(True)
            self.status_label.setText(f"扫描完成: {total_files} 个文件，点击「导入到向量库」开始导入")
        else:
            self.import_btn.setEnabled(False)
            self.status_label.setText("扫描完成: 未找到符合条件的文件")
    
    def on_scan_error(self, error_msg: str):
        """扫描错误"""
        self.scan_btn.setEnabled(True)
        self.import_progress.setVisible(False)
        self.status_label.setText(f"扫描失败: {error_msg}")
        QMessageBox.critical(self, "扫描错误", f"扫描文件夹失败:\n{error_msg}")
    
    def on_import_folder(self):
        """导入文件夹到向量库"""
        folder_path = self.folder_path_input.text().strip()
        if not folder_path:
            QMessageBox.warning(self, "警告", "请先选择文件夹路径")
            return
        
        file_types = self.get_selected_file_types()
        if not file_types:
            QMessageBox.warning(self, "警告", "请至少选择一种文件类型")
            return
        
        # 确认对话框
        reply = QMessageBox.question(
            self, "确认导入",
            f"确定要将文件夹中的文件导入到本地向量库吗？\n\n"
            f"文件夹: {folder_path}\n"
            f"文件数量: {len(self.scanned_files)} 个\n"
            f"文件类型: {', '.join(file_types)}\n"
            f"递归: {'是' if self.chk_recursive.isChecked() else '否'}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # 禁用按钮，显示进度
        self.import_btn.setEnabled(False)
        self.scan_btn.setEnabled(False)
        self.import_progress.setVisible(True)
        self.status_label.setText(f"正在导入: {folder_path}（可能需要较长时间）...")
        
        # 启动导入线程
        self.folder_worker = FolderImportWorker(
            folder_path, file_types, self.chk_recursive.isChecked()
        )
        self.folder_worker.finished.connect(self.on_import_finished)
        self.folder_worker.error.connect(self.on_import_error)
        self.folder_worker.start()
    
    def on_import_finished(self, result: dict):
        """导入完成"""
        self.import_btn.setEnabled(True)
        self.scan_btn.setEnabled(True)
        self.import_progress.setVisible(False)
        
        status = result.get("status", "")
        message = result.get("message", "")
        imported_count = result.get("imported_count", 0)
        total_files = result.get("total_files", 0)
        
        if status == "success":
            self.status_label.setText(
                f"✅ 导入成功: {imported_count}/{total_files} 个文件已导入向量库"
            )
            QMessageBox.information(
                self, "导入成功",
                f"文件夹导入成功！\n\n"
                f"成功导入: {imported_count} 个文件\n"
                f"扫描文件总数: {total_files}\n"
                f"这些文档现在可以通过「本地向量库」知识源进行检索。"
            )
        elif status == "warning":
            self.status_label.setText(f"⚠️ {message}")
            QMessageBox.warning(self, "导入警告", message)
        else:
            self.status_label.setText(f"导入完成: {message}")
            QMessageBox.information(self, "导入完成", message)
    
    def on_import_error(self, error_msg: str):
        """导入错误"""
        self.import_btn.setEnabled(True)
        self.scan_btn.setEnabled(True)
        self.import_progress.setVisible(False)
        self.status_label.setText(f"导入失败: {error_msg}")
        QMessageBox.critical(self, "导入错误", f"导入文件夹失败:\n{error_msg}")


def main():
    """启动应用"""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
