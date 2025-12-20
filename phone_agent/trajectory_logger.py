"""
Trajectory Logger for Open-AutoGLM
记录任务执行轨迹，用于 Web UI 可视化
"""

import os
import json
import uuid
import datetime
from io import BytesIO
from PIL import Image
from typing import Optional, List, Dict, Any

# 尝试导入 jsonlines，如果不可用则使用简单的 JSON 行格式
try:
    import jsonlines
    HAS_JSONLINES = True
except ImportError:
    HAS_JSONLINES = False


class TrajectoryLogger:
    """
    轨迹记录器 - 记录任务执行的每一步
    
    日志结构与 stepfunai/gelab-zero 兼容：
    - 第一条记录：session 配置信息 (task, model_config)
    - 后续记录：environment (截图) + action (思考+动作)
    """
    
    # 默认日志目录
    DEFAULT_LOG_DIR = "running_log/server_log/os-copilot-local-eval-logs/traces"
    DEFAULT_IMAGE_DIR = "running_log/server_log/os-copilot-local-eval-logs/images"
    
    def __init__(self, log_dir: Optional[str] = None, image_dir: Optional[str] = None):
        self.log_dir = log_dir or self.DEFAULT_LOG_DIR
        self.image_dir = image_dir or self.DEFAULT_IMAGE_DIR
        
        # 确保目录存在
        os.makedirs(self.log_dir, exist_ok=True)
        os.makedirs(self.image_dir, exist_ok=True)
        
        self.session_id: Optional[str] = None
        self.log_file: Optional[str] = None
        self.step_count = 0
    
    def start_session(self, task: str, model_name: str = "unknown", extra_info: Optional[Dict] = None) -> str:
        """
        开始新的 Session
        
        Args:
            task: 任务描述
            model_name: 模型名称
            extra_info: 额外信息
            
        Returns:
            session_id: 新创建的 Session ID
        """
        self.session_id = str(uuid.uuid4())
        self.log_file = os.path.join(self.log_dir, f"{self.session_id}.jsonl")
        self.step_count = 0
        
        # 记录 session 开始信息
        config_message = {
            "log_type": "session_start",
            "task": task,
            "task_type": "autoglm",
            "model_config": {
                "model_name": model_name
            },
            "extra_info": extra_info or {}
        }
        
        self._write_log(config_message)
        
        # 打印 Session ID 供 Web UI 捕获
        print(f"Session ID: {self.session_id}")
        
        return self.session_id
    
    def log_step(
        self,
        screenshot: Optional[Image.Image] = None,
        screenshot_base64: Optional[str] = None,
        thinking: str = "",
        action: Optional[Dict[str, Any]] = None,
        action_type: str = "unknown",
        user_comment: str = ""
    ):
        """
        记录一个执行步骤
        
        Args:
            screenshot: PIL Image 截图
            screenshot_base64: base64 编码的截图（如果没有 PIL Image）
            thinking: 模型思考内容
            action: 动作字典
            action_type: 动作类型
            user_comment: 用户评论/反馈
        """
        if not self.session_id:
            return
        
        self.step_count += 1
        
        # 保存截图
        image_path = ""
        if screenshot:
            image_path = self._save_image(screenshot, f"step_{self.step_count}")
        elif screenshot_base64:
            # 从 base64 解码并保存
            try:
                import base64
                # 去掉 data:image/xxx;base64, 前缀
                if "," in screenshot_base64:
                    screenshot_base64 = screenshot_base64.split(",")[1]
                image_data = base64.b64decode(screenshot_base64)
                image = Image.open(BytesIO(image_data))
                image_path = self._save_image(image, f"step_{self.step_count}")
            except Exception as e:
                print(f"[TrajectoryLogger] 保存截图失败: {e}")
        
        # 构建日志消息
        log_message = {
            "environment": {
                "image": image_path,
                "user_comment": user_comment
            },
            "action": {
                "cot": thinking,  # Chain of Thought
                "action_type": action_type,
                **(action or {})
            }
        }
        
        self._write_log(log_message)
    
    def end_session(self, final_message: str = ""):
        """结束当前 Session"""
        if not self.session_id:
            return
        
        # 可选：记录结束信息
        if final_message:
            self._write_log({
                "log_type": "session_end",
                "message": final_message
            })
        
        self.session_id = None
        self.log_file = None
        self.step_count = 0
    
    def _write_log(self, message_dict: Dict[str, Any]):
        """写入日志"""
        if not self.log_file:
            return
        
        log_entry = {
            "session_id": self.session_id,
            "timestamp": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "message": message_dict
        }
        
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
        except Exception as e:
            print(f"[TrajectoryLogger] 写入日志失败: {e}")
    
    def _save_image(self, image: Image.Image, image_name: str) -> str:
        """保存图片到 image_dir"""
        if not self.session_id:
            return ""
        
        try:
            # 转换为 RGB 并压缩为 JPEG
            buffered = BytesIO()
            image = image.convert('RGB')
            image.save(buffered, format="JPEG", quality=85)
            image_data = buffered.getvalue()
            
            image_path = os.path.join(self.image_dir, f"{self.session_id}_{image_name}.jpeg")
            with open(image_path, "wb") as f:
                f.write(image_data)
            
            return image_path
        except Exception as e:
            print(f"[TrajectoryLogger] 保存图片失败: {e}")
            return ""
    
    @classmethod
    def read_session_logs(cls, session_id: str, log_dir: Optional[str] = None) -> List[Dict]:
        """读取指定 session 的日志"""
        log_dir = log_dir or cls.DEFAULT_LOG_DIR
        log_file = os.path.join(log_dir, f"{session_id}.jsonl")
        
        if not os.path.exists(log_file):
            return []
        
        logs = []
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        logs.append(json.loads(line))
        except Exception as e:
            print(f"[TrajectoryLogger] 读取日志失败: {e}")
        
        return logs
    
    @classmethod
    def get_available_sessions(cls, log_dir: Optional[str] = None, limit: int = 20) -> List[str]:
        """获取所有可用的 session 列表"""
        import glob
        
        log_dir = log_dir or cls.DEFAULT_LOG_DIR
        if not os.path.exists(log_dir):
            return []
        
        sessions = []
        for f in glob.glob(os.path.join(log_dir, "*.jsonl")):
            session_id = os.path.basename(f).replace(".jsonl", "")
            mtime = os.path.getmtime(f)
            sessions.append((session_id, mtime))
        
        # 按时间倒序
        sessions.sort(key=lambda x: x[1], reverse=True)
        return [s[0] for s in sessions[:limit]]


# 全局单例
_global_logger: Optional[TrajectoryLogger] = None


def get_trajectory_logger() -> TrajectoryLogger:
    """获取全局轨迹记录器"""
    global _global_logger
    if _global_logger is None:
        _global_logger = TrajectoryLogger()
    return _global_logger
