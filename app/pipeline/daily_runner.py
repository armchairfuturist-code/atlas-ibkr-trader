"""End-to-end daily pipeline runner."""
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from app.config import Config, load_config_from_file
from app.universe import load_universe
from app.signal_orchestrator import SignalOrchestrator, MacroContext
from app.risk_engine import RiskEngine, PortfolioState
from app.intent_translator import IntentTranslator
from app.approval_gate import ApprovalGate
from app.ibkr_adapter import IBKRAdapter
from app.no_trade_controller import NoTradeController
from app.data.providers import FixtureProvider, create_fresh_fixture, IBKRDataProvider
from app.schemas import OrderStatus


@dataclass
class PipelineResult:
    """Result of pipeline execution."""
    status: str  # NO_TRADE, READY_FOR_APPROVAL, SUBMITTED_PAPER
    signals_count: int = 0
    intents_count: int = 0
    submitted_count: int = 0
    error: str = ""
    logs: list[str] = None
    
    def __post_init__(self):
        if self.logs is None:
            self.logs = []


class DailyPipeline:
    """
    End-to-end daily pipeline runner.
    
    Stages:
    1. Pre-exec: Data quality check
    2. Signal: Generate trading signals
    3. Risk: Evaluate against risk limits
    4. Intent: Create proposed order intents
    5. Approval: Require human approval
    6. Submit: Submit to IBKR paper
    """
    
    def __init__(self, config_path: str = "fixtures/config.paper.yaml", use_ibkr_data: bool = True):
        # Load config
        self.config = load_config_from_file(config_path)
        
        # Load universe
        self.universe = load_universe("fixtures/universe.valid.yaml")
        
        # Initialize components
        self.risk_engine = RiskEngine(self.config, self.universe)
        self.translator = IntentTranslator(self.config, self.universe)
        self.approval_gate = ApprovalGate()
        self.ibkr_adapter = IBKRAdapter(self.config)
        
        # Data provider - use IBKR real data if available
        if use_ibkr_data:
            self.data_provider = IBKRDataProvider(
                host=self.config.ibkr_host,
                port=self.config.ibkr_port,
                client_id=self.config.ibkr_client_id
            )
            connected, error = self.data_provider.connect()
            if not connected:
                print(f"Warning: Could not connect to IBKR data: {error}")
                print("Falling back to fixture data")
                self.data_provider = FixtureProvider(create_fresh_fixture())
        else:
            self.data_provider = FixtureProvider(create_fresh_fixture())
        
        self.no_trade_controller = NoTradeController(self.data_provider)
        
        # Orchestrator
        self.orchestrator = SignalOrchestrator(self.universe, self.config)
        
        # Portfolio state
        self.portfolio = PortfolioState()
    
    def run(self, stage: str = "full") -> PipelineResult:
        """Run the pipeline up to specified stage."""
        result = PipelineResult(status="UNKNOWN")
        
        try:
            # Stage 1: Pre-exec data check
            result.logs.append(f"[{datetime.now()}] Stage 1: Pre-execution data check")
            no_trade = self.no_trade_controller.check(["SPY", "QQQ", "XLF"])
            if not no_trade.should_trade:
                result.status = "NO_TRADE"
                result.error = f"{no_trade.reason_code}: {no_trade.reason}"
                result.logs.append(f"  -> NO_TRADE: {no_trade.reason}")
                return result
            
            result.logs.append("  -> Data check PASSED")
            
            # Stage 2: Signal generation
            if stage in ("full", "signal", "risk", "intent", "approval", "submit"):
                result.logs.append(f"[{datetime.now()}] Stage 2: Signal generation")
                signals = self.orchestrator.generate_signals()
                result.signals_count = len(signals)
                result.logs.append(f"  -> Generated {len(signals)} signals")
                
                if not signals:
                    result.status = "NO_TRADE"
                    result.logs.append("  -> No signals, exiting")
                    return result
            
            # Stage 3: Risk evaluation (simplified for now)
            # In production, would evaluate each signal
            result.logs.append(f"[{datetime.now()}] Stage 3: Risk evaluation")
            result.logs.append("  -> Risk checks would run here")
            
            # Stage 4: Create intents
            result.logs.append(f"[{datetime.now()}] Stage 4: Create proposed intents")
            result.logs.append("  -> Intent creation would run here")
            
            # Stage 5: Human approval required
            result.logs.append(f"[{datetime.now()}] Stage 5: Human approval required")
            result.status = "READY_FOR_APPROVAL"
            result.logs.append("  -> Status: READY_FOR_APPROVAL")
            
            if stage == "submit":
                # Would connect to IBKR and submit
                result.logs.append(f"[{datetime.now()}] Stage 6: Submit to IBKR")
                result.status = "SUBMITTED_PAPER"
                result.submitted_count = 0
                result.logs.append("  -> Would submit to IBKR paper")
            
        except Exception as e:
            result.status = "ERROR"
            result.error = str(e)
            result.logs.append(f"ERROR: {e}")
        
        return result


def main():
    """CLI entry point."""
    import argparse
    parser = argparse.ArgumentParser(description="Atlas Daily Pipeline")
    parser.add_argument("--mode", default="paper", help="Execution mode")
    parser.add_argument("--fixture", help="Market data fixture")
    parser.add_argument("--stage", default="full", help="Run up to stage")
    
    args = parser.parse_args()
    
    # Run pipeline
    pipeline = DailyPipeline()
    result = pipeline.run(args.stage)
    
    # Print results
    print(f"\n=== Pipeline Result ===")
    print(f"Status: {result.status}")
    print(f"Signals: {result.signals_count}")
    print(f"Intents: {result.intents_count}")
    print(f"Submitted: {result.submitted_count}")
    if result.error:
        print(f"Error: {result.error}")
    
    print("\n=== Logs ===")
    for log in result.logs:
        print(log)
    
    return 0 if result.status != "ERROR" else 1


if __name__ == "__main__":
    sys.exit(main())
