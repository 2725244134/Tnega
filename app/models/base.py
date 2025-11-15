"""
============================================
数据库基础模型
============================================
SQLAlchemy 基础模型定义
"""

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, func
from sqlalchemy.ext.declarative import as_declarative, declared_attr
from sqlalchemy.orm import Mapped, mapped_column


@as_declarative()
class Base:
    """
    数据库模型基类

    提供：
    - 自动生成的表名（基于类名）
    - 创建时间和更新时间字段
    - 通用的 CRUD 方法基础
    """

    id: Any
    __name__: str

    # 自动生成的表名
    @declared_attr
    def __tablename__(cls) -> str:
        """将类名转换为小写+下划线的表名"""
        import re
        # 将驼峰命名转换为下划线命名
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', cls.__name__)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

    # 创建时间
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="创建时间"
    )

    # 更新时间
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="更新时间"
    )

    def __repr__(self) -> str:
        """字符串表示"""
        return f"<{self.__class__.__name__}(id={self.id})>"

    def to_dict(self) -> dict:
        """
        转换为字典

        Returns:
            dict: 模型字段字典
        """
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }


class TimestampMixin:
    """
    时间戳混入类

    为模型提供创建时间和更新时间字段
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="创建时间"
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="更新时间"
    )


class SoftDeleteMixin:
    """
    软删除混入类

    为模型提供软删除功能
    """

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="删除时间"
    )

    @property
    def is_deleted(self) -> bool:
        """是否已删除"""
        return self.deleted_at is not None