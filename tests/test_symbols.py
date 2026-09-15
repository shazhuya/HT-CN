import pytest

from htcn.data.models import Board, Exchange
from htcn.data.symbols import classify_symbol, instrument_id_from_symbol, symbol_from_instrument_id


def test_sse_star_symbol() -> None:
    exchange, board = classify_symbol("688256")
    assert exchange is Exchange.SSE
    assert board is Board.STAR
    assert instrument_id_from_symbol("688256") == "SSE.688256"


def test_szse_chinext_symbol() -> None:
    exchange, board = classify_symbol("300820")
    assert exchange is Exchange.SZSE
    assert board is Board.CHINEXT
    assert symbol_from_instrument_id("SZSE.300820") == "300820"


def test_bse_symbol() -> None:
    exchange, board = classify_symbol("920001")
    assert exchange is Exchange.BSE
    assert board is Board.BSE


def test_mismatched_instrument_id_rejected() -> None:
    with pytest.raises(ValueError):
        symbol_from_instrument_id("SZSE.688256")
