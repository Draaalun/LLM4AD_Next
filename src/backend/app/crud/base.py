"""
通用 CRUD 基类模块。

提供基于 SQLModel 的增删改查泛型基类，
子类只需继承并指定模型类型即可获得标准 CRUD 能力。
"""

from typing import Any

from sqlmodel import Session, SQLModel, func, select


class BaseCRUD[ModelType: SQLModel, CreateSchemaType: SQLModel, UpdateSchemaType: SQLModel]:
    """同步通用 CRUD 基类"""

    def __init__(self, model: type[ModelType], session: Session):
        self.model = model
        self.session = session

    def get(self, pk: Any) -> ModelType | None:
        """根据主键获取单条记录"""
        return self.session.get(self.model, pk)

    def get_multi(self, *, skip: int = 0, limit: int = 100) -> list[ModelType]:
        """获取多条记录，支持分页"""
        statement = select(self.model).offset(skip).limit(limit)
        result = self.session.exec(statement)
        return result.all()

    def create(self, obj_in: CreateSchemaType) -> ModelType:
        """创建一条新记录"""
        db_obj = self.model(**obj_in.model_dump())
        self.session.add(db_obj)
        self.session.commit()
        self.session.refresh(db_obj)
        return db_obj

    def update(self, pk: Any, obj_in: UpdateSchemaType) -> ModelType | None:
        """更新一条记录（部分更新）"""
        db_obj = self.get(pk)
        if not db_obj:
            return None
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        self.session.add(db_obj)
        self.session.commit()
        self.session.refresh(db_obj)
        return db_obj

    def remove(self, pk: Any) -> ModelType | None:
        """删除一条记录，返回被删除的对象"""
        db_obj = self.get(pk)
        if not db_obj:
            return None
        self.session.delete(db_obj)
        self.session.commit()
        return db_obj

    def count(self) -> int:
        """统计总记录数"""
        statement = select(func.count()).select_from(self.model)
        result = self.session.exec(statement)
        return result.one()
