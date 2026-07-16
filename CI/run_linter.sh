#!/usr/bin/env bash

# =================================================================
# TriggerForge - Local CI Quality Assurance Script
# Author: zybcode
# Description: One-click script to format and lint the codebase.
#              Automatically detects Hatch and falls back to global pip tools.
# =================================================================

# 发生错误时立即退出，并确保管道命令的错误能被捕获
set -eo pipefail

# 颜色控制台输出
GREEN="\033[0;32m"
YELLOW="\033[1;33m"
RED="\033[0;31m"
BLUE="\033[0;34m"
NC="\033[0m" # No Color

# 获取项目根目录 (假设该脚本放在 project_root/ci/ 下)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 1. 检查 Hatch 是否可用
if command -v hatch &> /dev/null; then
    log_info "Detected 'hatch'. Running linting and formatting via Hatch environment..."
    
    log_info "Step 1/2: Formatting codebase with Black..."
    hatch run format
    
    log_info "Step 2/2: Running static type analysis and style checks..."
    if hatch run lint; then
        log_success "All style and type checks passed flawlessly!"
    else
        log_error "Linter failed. Please resolve the issues above before pushing."
        exit 1
    fi

# 2. 如果没有 Hatch，尝试回退到全局环境的 Python 格式化工具
else
    log_warning "'hatch' not found. Attempting to fall back to global virtual environment or pip tools..."
    
    # 检查 Black 是否安装
    if command -v black &> /dev/null; then
        log_info "Formatting codebase with global 'black'..."
        black src tests
    else
        log_warning "'black' is not installed. Skipping automatic formatting."
    fi

    # 检查 Mypy 是否安装
    if command -v mypy &> /dev/null; then
        log_info "Running static type analysis with global 'mypy'..."
        if mypy src; then
            log_success "Mypy static type checking passed!"
        else
            log_error "Mypy static type checking failed."
            exit 1
        fi
    else
        log_warning "'mypy' is not installed. Skipping static type checks."
    fi
    
    log_warning "To get the complete linting suite, we highly recommend installing Hatch: 'pip install hatch'"
fi