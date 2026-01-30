from dataclass import dataclass 

@dataclass(frozen=True)
class Instrument:
    symbol: str
    asset_class: str 
    currency: str 
    tick_size: float
    contract_multiplier: float 
    trading_cost_bps: float 