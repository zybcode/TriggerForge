"""
TriggerForge - Clerk Archiver Unit Tests
Author: zybcode
Description: Comprehensive unit tests for ClerkArchiver, validating atomic moves,
             directory self-healing, duplicate avoidance, and error boundaries.
"""

import pytest
from triggerforge.core.clerk.archiver import ClerkArchiver


def test_archive_success_basic(temp_workspace, dummy_file):
    """
    测试基础的成功归档功能。
    验证源文件被正确移动，原文件不再存在，目标文件存在且内容一致。
    """
    archiver = ClerkArchiver()
    success_dir = temp_workspace / "success"

    # 执行归档
    final_path = archiver.archive_success(dummy_file, success_dir)

    assert final_path.exists()
    assert final_path.parent == success_dir
    assert not dummy_file.exists()
    assert final_path.read_text(encoding="utf-8") == "TriggerForge unit test payload."


def test_archive_error_basic(temp_workspace, dummy_file):
    """
    测试基础的故障隔离功能。
    验证源文件被正确移动至 error 隔离目录。
    """
    archiver = ClerkArchiver()
    error_dir = temp_workspace / "error"

    final_path = archiver.archive_error(dummy_file, error_dir)

    assert final_path.exists()
    assert final_path.parent == error_dir
    assert not dummy_file.exists()


def test_directory_self_healing(temp_workspace, dummy_file):
    """
    测试目录自愈机制。
    验证当目标归档目录（多级深层目录）在物理上不存在时，归档器能自动递归创建它。
    """
    archiver = ClerkArchiver()
    deep_success_dir = temp_workspace / "nested" / "deep" / "success_zone"

    # 确保开始前该深层目录绝对不存在
    assert not deep_success_dir.exists()

    final_path = archiver.archive_success(dummy_file, deep_success_dir)

    assert deep_success_dir.exists()
    assert final_path.exists()
    assert final_path.parent == deep_success_dir


def test_duplicate_avoidance_with_timestamp(temp_workspace, dummy_file):
    """
    测试同名文件冲突避免逻辑。
    当目标目录下已经有一个同名文件时，验证归档器是否能自动重命名（引入时间戳后缀）并成功移动。
    """
    archiver = ClerkArchiver()
    success_dir = temp_workspace / "success"
    success_dir.mkdir(parents=True, exist_ok=True)

    # 1. 在目标目录下提前制造一个同名的阻碍文件
    obstacle_path = success_dir / dummy_file.name
    obstacle_path.write_text("existing old file", encoding="utf-8")

    # 2. 执行归档
    final_path = archiver.archive_success(dummy_file, success_dir)

    # 3. 断言校验
    assert not dummy_file.exists()
    assert obstacle_path.exists()
    assert obstacle_path.read_text(encoding="utf-8") == "existing old file"
    assert final_path.exists()
    assert final_path != obstacle_path
    assert "_" in final_path.stem  # 校验是否带有了时间戳下划线


def test_archive_source_file_not_found(temp_workspace):
    """
    测试异常边界：源文件不存在。
    验证当试图归档一个根本不存在的文件时，归档器能正确抛出 FileNotFoundError。
    """
    archiver = ClerkArchiver()
    non_existent_file = temp_workspace / "ghost.txt"
    success_dir = temp_workspace / "success"

    with pytest.raises(FileNotFoundError) as exc_info:
        archiver.archive_success(non_existent_file, success_dir)

    assert "Source file not found" in str(exc_info.value)
