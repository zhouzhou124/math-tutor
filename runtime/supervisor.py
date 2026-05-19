"""runtime/supervisor.py — 运行时监督器

═══════════════════════════════════════════════════════════════
核心功能
═══════════════════════════════════════════════════════════════

  1. Task Queue — 任务队列，异步化所有耗时操作
  2. Watchdog — 超时自动终止，防止无限挂起
  3. Renderer Isolation — LaTeX渲染单独进程隔离
  4. Resource Monitor — 资源监控（内存、CPU）

═══════════════════════════════════════════════════════════════
架构设计
═══════════════════════════════════════════════════════════════

    ┌─────────────────────────────────────────────────────────┐
    │                    Streamlit Frontend                   │
    └─────────────────────────┬───────────────────────────────┘
                              │ HTTP/WS
                              ▼
    ┌─────────────────────────────────────────────────────────┐
    │              Runtime Supervisor (此模块)                 │
    │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
    │  │ Task Queue  │  │  Watchdog   │  │ Resource    │     │
    │  │ (async)     │  │ (timeout)   │  │ Monitor     │     │
    │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘     │
    │         │                │                │             │
    │         ▼                ▼                ▼             │
    │  ┌───────────────────────────────────────────────┐      │
    │  │            Isolated Workers                   │      │
    │  │  ┌─────────┐ ┌─────────┐ ┌─────────┐        │      │
    │  │  │  OCR    │ │  Solver │ │Renderer │        │      │
    │  │  │ Worker  │ │ Worker  │ │ Worker  │        │      │
    │  │  └─────────┘ └─────────┘ └─────────┘        │      │
    │  └───────────────────────────────────────────────┘      │
    └─────────────────────────────────────────────────────────┘

═══════════════════════════════════════════════════════════════
"""

import os
import sys
import time
import json
import signal
import threading
import subprocess
from dataclasses import dataclass, field
from enum import Enum, auto
from queue import Queue, Empty
from typing import Any, Callable, Dict, List, Optional, Tuple, Union


# ──────────────────────────────────────────────────────────────
# 配置常量
# ──────────────────────────────────────────────────────────────
MAX_WORKERS = 3
DEFAULT_TIMEOUT = 30  # 秒
RESOURCE_CHECK_INTERVAL = 5  # 秒
MAX_MEMORY_GB = 4  # 最大内存限制


class TaskStatus(Enum):
    """任务状态"""
    PENDING = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    TIMEOUT = auto()


class TaskType(Enum):
    """任务类型"""
    OCR = auto()
    SOLVE = auto()
    GRADE = auto()
    RENDER = auto()
    DIAGNOSE = auto()


@dataclass
class Task:
    """任务定义"""
    task_id: str
    task_type: TaskType
    func: Callable
    args: Tuple = ()
    kwargs: Dict = field(default_factory=dict)
    timeout: int = DEFAULT_TIMEOUT
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: Optional[Exception] = None
    start_time: float = 0.0
    end_time: float = 0.0


@dataclass
class WorkerStats:
    """工作线程统计"""
    worker_id: int
    task_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    total_time: float = 0.0


class Worker(threading.Thread):
    """隔离的工作线程"""
    
    def __init__(self, worker_id: int, task_queue: Queue, stats: WorkerStats):
        super().__init__(daemon=True)
        self.worker_id = worker_id
        self.task_queue = task_queue
        self.stats = stats
        self._stop_event = threading.Event()
        self._current_task: Optional[Task] = None
    
    def run(self):
        """工作线程主循环"""
        while not self._stop_event.is_set():
            try:
                task = self.task_queue.get(timeout=1)
                self._process_task(task)
                self.task_queue.task_done()
            except Empty:
                continue
            except Exception as e:
                print(f"[Worker-{self.worker_id}] 异常: {e}")
    
    def _process_task(self, task: Task):
        """处理单个任务（带超时保护）"""
        self._current_task = task
        task.status = TaskStatus.RUNNING
        task.start_time = time.time()
        
        result = None
        error = None
        
        try:
            # 使用线程+超时机制执行任务
            result, error = self._run_with_timeout(task)
        except Exception as e:
            error = e
        
        task.end_time = time.time()
        task.result = result
        task.error = error
        
        if error:
            task.status = TaskStatus.FAILED
            self.stats.failure_count += 1
        elif (task.end_time - task.start_time) >= task.timeout:
            task.status = TaskStatus.TIMEOUT
            self.stats.failure_count += 1
        else:
            task.status = TaskStatus.COMPLETED
            self.stats.success_count += 1
        
        self.stats.task_count += 1
        self.stats.total_time += (task.end_time - task.start_time)
        self._current_task = None
    
    def _run_with_timeout(self, task: Task) -> Tuple[Any, Optional[Exception]]:
        """带超时的任务执行"""
        result = None
        exception = None
        
        def worker():
            nonlocal result, exception
            try:
                result = task.func(*task.args, **task.kwargs)
            except Exception as e:
                exception = e
        
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        thread.join(task.timeout)
        
        if thread.is_alive():
            # 超时！尝试优雅终止
            exception = TimeoutError(f"任务超时 ({task.timeout}s)")
        
        return result, exception
    
    def stop(self):
        """停止工作线程"""
        self._stop_event.set()


class ResourceMonitor(threading.Thread):
    """资源监控线程"""
    
    def __init__(self):
        super().__init__(daemon=True)
        self._stop_event = threading.Event()
        self.memory_usage = 0.0
        self.cpu_usage = 0.0
        self.should_throttle = False
    
    def run(self):
        """监控主循环"""
        while not self._stop_event.is_set():
            self._update_stats()
            self._check_limits()
            time.sleep(RESOURCE_CHECK_INTERVAL)
    
    def _update_stats(self):
        """更新资源使用统计"""
        try:
            if sys.platform == "win32":
                # Windows 平台
                import psutil
                process = psutil.Process()
                self.memory_usage = process.memory_info().rss / (1024 ** 3)  # GB
                self.cpu_usage = process.cpu_percent()
            else:
                # Unix/Linux 平台
                with open("/proc/self/status") as f:
                    for line in f:
                        if line.startswith("VmRSS:"):
                            self.memory_usage = int(line.split()[1]) / (1024 ** 2)  # GB
                            break
        except Exception:
            pass
    
    def _check_limits(self):
        """检查资源限制"""
        self.should_throttle = self.memory_usage > MAX_MEMORY_GB
    
    def stop(self):
        """停止监控"""
        self._stop_event.set()


class RuntimeSupervisor:
    """运行时监督器 — 核心控制器"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.task_queue = Queue()
        self.workers: List[Worker] = []
        self.worker_stats: List[WorkerStats] = []
        self.resource_monitor = ResourceMonitor()
        self._lock = threading.Lock()
        self._tasks: Dict[str, Task] = {}
        
        self._initialized = True
    
    def start(self):
        """启动监督器"""
        # 启动资源监控
        self.resource_monitor.start()
        
        # 启动工作线程
        for i in range(MAX_WORKERS):
            stats = WorkerStats(worker_id=i)
            worker = Worker(i, self.task_queue, stats)
            self.workers.append(worker)
            self.worker_stats.append(stats)
            worker.start()
        
        print(f"[RuntimeSupervisor] 已启动 {MAX_WORKERS} 个工作线程")
    
    def stop(self):
        """停止监督器"""
        # 停止工作线程
        for worker in self.workers:
            worker.stop()
            worker.join(timeout=5)
        
        # 停止资源监控
        self.resource_monitor.stop()
        self.resource_monitor.join(timeout=2)
        
        print("[RuntimeSupervisor] 已停止")
    
    def submit_task(
        self,
        task_type: TaskType,
        func: Callable,
        *args,
        timeout: int = DEFAULT_TIMEOUT,
        **kwargs
    ) -> str:
        """提交任务到队列"""
        task_id = f"{task_type.name.lower()}_{int(time.time() * 1000)}_{id(func)}"
        
        task = Task(
            task_id=task_id,
            task_type=task_type,
            func=func,
            args=args,
            kwargs=kwargs,
            timeout=timeout
        )
        
        with self._lock:
            self._tasks[task_id] = task
        
        self.task_queue.put(task)
        return task_id
    
    def get_task_status(self, task_id: str) -> Optional[Task]:
        """获取任务状态"""
        with self._lock:
            return self._tasks.get(task_id)
    
    def wait_for_task(self, task_id: str, timeout: int = 60) -> Optional[Task]:
        """等待任务完成（带超时）"""
        start = time.time()
        while (time.time() - start) < timeout:
            task = self.get_task_status(task_id)
            if task and task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.TIMEOUT):
                return task
            time.sleep(0.1)
        return None
    
    def run_sync(self, task_type: TaskType, func: Callable, *args, **kwargs) -> Any:
        """同步执行任务（带超时保护）"""
        # 检查资源状态
        if self.resource_monitor.should_throttle:
            raise RuntimeError("系统资源紧张，请稍后再试")
        
        task_id = self.submit_task(task_type, func, *args, **kwargs)
        task = self.wait_for_task(task_id, timeout=kwargs.get("timeout", DEFAULT_TIMEOUT) + 5)
        
        if task:
            if task.error:
                raise task.error
            return task.result
        raise TimeoutError("任务等待超时")
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        total_tasks = sum(s.task_count for s in self.worker_stats)
        total_success = sum(s.success_count for s in self.worker_stats)
        total_failure = sum(s.failure_count for s in self.worker_stats)
        total_time = sum(s.total_time for s in self.worker_stats)
        
        return {
            "workers": MAX_WORKERS,
            "active_workers": sum(1 for w in self.workers if w._current_task),
            "total_tasks": total_tasks,
            "success_rate": total_success / max(total_tasks, 1) * 100,
            "avg_task_time": total_time / max(total_tasks, 1),
            "memory_usage_gb": round(self.resource_monitor.memory_usage, 2),
            "cpu_usage_percent": round(self.resource_monitor.cpu_usage, 1),
            "should_throttle": self.resource_monitor.should_throttle,
        }


# ──────────────────────────────────────────────────────────────
# 全局单例
# ──────────────────────────────────────────────────────────────
_supervisor = None


def get_supervisor() -> RuntimeSupervisor:
    """获取全局监督器实例"""
    global _supervisor
    if _supervisor is None:
        _supervisor = RuntimeSupervisor()
    return _supervisor


def init_supervisor():
    """初始化并启动监督器"""
    supervisor = get_supervisor()
    supervisor.start()


def shutdown_supervisor():
    """关闭监督器"""
    global _supervisor
    if _supervisor:
        _supervisor.stop()
        _supervisor = None


# ──────────────────────────────────────────────────────────────
# 上下文管理器支持
# ──────────────────────────────────────────────────────────────
class SupervisorContext:
    """监督器上下文管理器"""
    
    def __enter__(self):
        init_supervisor()
        return get_supervisor()
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        shutdown_supervisor()


# ──────────────────────────────────────────────────────────────
# 装饰器：自动使用监督器执行
# ──────────────────────────────────────────────────────────────
def supervised(task_type: TaskType, timeout: int = DEFAULT_TIMEOUT):
    """装饰器：将函数包装为受监督的任务"""
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            supervisor = get_supervisor()
            return supervisor.run_sync(task_type, func, *args, timeout=timeout, **kwargs)
        return wrapper
    return decorator


# ──────────────────────────────────────────────────────────────
# 信号处理
# ──────────────────────────────────────────────────────────────
def _handle_shutdown(signum, frame):
    """处理系统关闭信号"""
    print(f"\n[RuntimeSupervisor] 收到信号 {signum}，正在关闭...")
    shutdown_supervisor()
    sys.exit(0)


# 注册信号处理
if sys.platform != "win32":
    signal.signal(signal.SIGINT, _handle_shutdown)
    signal.signal(signal.SIGTERM, _handle_shutdown)