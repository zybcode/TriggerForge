"""
TriggerForge - Event Buffer Queue Module
Author: zybcode
Description: Thread-safe event buffer queue mediating file events between 
             the Sentry monitors and the downstream ForgeCore executors.
"""

import queue
from pathlib import Path
from typing import Optional, List


class EventBufferQueue:
    """
    线程安全的事件缓冲队列。
    作为 Sentry（事件产生端）与 ForgeCore（事件消费端）之间的缓冲区。
    """
    def __init__(self, maxsize: int = 0):
        """
        Args:
            maxsize: 队列最大容量限制。若为 0 或负数，则队列长度无限制。
        """
        self._queue: queue.Queue[Path] = queue.Queue(maxsize=maxsize)
        # track enqueued items to enforce uniqueness before consumption
        self._enqueued_set: set[str] = set()

    def put(self, file_path: Path, timeout: Optional[float] = None) -> bool:
        """
        向队列中安全地投递一个待处理的文件路径。
        
        Args:
            file_path: 触发事件的目标文件绝对路径
            timeout: 可选的超时时间（秒）。如果队列满了，在超时时间内阻塞等待
            
        Returns:
            bool: 投递成功返回 True，超时或异常导致失败导致失败
        """
        try:
            self._queue.put(file_path, block=True, timeout=timeout)
            self._enqueued_set.add(str(file_path))
            return True
        except queue.Full:
            return False

    def get(self, timeout: Optional[float] = None) -> Optional[Path]:
        """
        从队列中消费获取一个文件路径。如果队列为空，将进入阻塞状态。
        
        Args:
            timeout: 可选的阻塞超时时间（秒）。若为 None 且无数据，则无限期阻塞
            
        Returns:
            Optional[Path]: 返回获取到的文件 Path 对象，若超时未获取到则返回 None
        """
        try:
            item = self._queue.get(block=True, timeout=timeout)
            # allow item to be re-enqueued in future
            key = str(item)
            self._enqueued_set.discard(key)
            return item
        except queue.Empty:
            return None

    def get_nowait(self) -> Optional[Path]:
        """Non-blocking get; returns None if empty."""
        try:
            item = self._queue.get_nowait()
            self._enqueued_set.discard(str(item))
            return item
        except queue.Empty:
            return None

    def task_done(self) -> None:
        """
        通知队列前一个被弹出的任务（通过 get 获取）已成功执行完毕。
        常用于优雅停机或需要协同等待的流水线。
        """
        self._queue.task_done()

    def qsize(self) -> int:
        """
        获取当前积压的任务近似数量。
        """
        return self._queue.qsize()

    # Backwards-compatible alias used by unit tests
    def size(self) -> int:
        return self.qsize()

    def empty(self) -> bool:
        """
        判断当前队列是否为空。
        """
        return self._queue.empty()

    def clear(self) -> List[Path]:
        """
        清空当前队列中所有的待处理任务并返回它们。
        常用于系统重载或紧急熔断场景。
        """
        dropped_tasks: List[Path] = []
        while not self._queue.empty():
            try:
                # 使用 block=False 防止多线程竞争下发生死锁
                task = self._queue.get_nowait()
                dropped_tasks.append(task)
                self._queue.task_done()
            except queue.Empty:
                break
        # 清空去重集合
        self._enqueued_set.clear()
        return dropped_tasks