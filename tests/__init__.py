# ============================================
# Tests 包初始化文件
# ============================================
# 配置测试环境的路径和公共设置

import sys
from pathlib import Path

# 将项目根目录添加到 Python 路径
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
