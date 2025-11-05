# ============================================
# System Prompt 加载器
# ============================================
# 从 markdown 文件加载 System Prompt，实现配置与代码分离

from pathlib import Path

from loguru import logger

# ============================================
# 默认 Prompt 文件路径
# ============================================

PROMPT_FILE = Path(__file__).parent / "search_rule.md"


# ============================================
# Prompt 加载函数
# ============================================


def load_system_prompt(prompt_file: Path = PROMPT_FILE) -> str:
    """
    从 markdown 文件加载 System Prompt

    设计原则：
    - Prompt 工程与代码分离
    - 便于版本控制和迭代
    - 直接加载整个文件内容

    Args:
        prompt_file: Prompt 文件路径

    Returns:
        str: System Prompt 内容

    Raises:
        FileNotFoundError: 文件不存在

    Examples:
        >>> prompt = load_system_prompt()
        >>> assert len(prompt) > 0
    """
    if not prompt_file.exists():
        raise FileNotFoundError(f"Prompt 文件不存在: {prompt_file}")

    logger.debug(f"加载 System Prompt: {prompt_file}")

    content = prompt_file.read_text(encoding="utf-8")

    logger.debug(f"成功加载 System Prompt，长度: {len(content)} 字符")

    return content
