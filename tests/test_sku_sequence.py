import queue
import threading

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import Item, SKUCounter
from app.services.sku import assign_instance_seq


def _make_item() -> Item:
    return Item(
        id=1,
        template_id=10,
        product_code="BLK-98-20-A2",
        uom="EA",
        attributes={},
        attribute_hash="hash",
        track_lots=True,
    )


def test_assign_instance_seq_increments(tmp_path) -> None:
    db_path = tmp_path / "sku_counter.sqlite"
    engine = create_engine(f"sqlite:///{db_path}")
    SKUCounter.__table__.create(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    item = _make_item()

    with SessionLocal() as db:
        with db.begin():
            seq1 = assign_instance_seq(db, item)

    with SessionLocal() as db:
        with db.begin():
            seq2 = assign_instance_seq(db, item)

    assert seq1 == 1
    assert seq2 == 2


def test_assign_instance_seq_concurrent(tmp_path) -> None:
    db_path = tmp_path / "sku_counter_concurrent.sqlite"
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )
    SKUCounter.__table__.create(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    item = _make_item()

    results: queue.Queue[int] = queue.Queue()
    barrier = threading.Barrier(2)

    def worker() -> None:
        with SessionLocal() as db:
            with db.begin():
                barrier.wait()
                seq = assign_instance_seq(db, item)
            results.put(seq)

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    seqs = sorted(results.get_nowait() for _ in range(2))
    assert seqs == [1, 2]
