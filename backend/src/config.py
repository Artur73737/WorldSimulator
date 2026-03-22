from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://worldsim:worldsim_pass@localhost:5432/worldsimulation"
    )

    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0")

    # NVIDIA / LLM API
    llm_api_key: str = Field(default="")
    llm_base_url: str = Field(default="https://integrate.api.nvidia.com/v1")

    # Simulation Settings
    simulation_seed: str = Field(default="worldsim_default")
    max_agents_default: int = Field(default=8)
    max_turns_per_debate: int = Field(default=5)

    # Rate Limiting (40 RPM)
    max_rpm: int = Field(default=40)
    min_request_interval: float = Field(default=1.5)
    backoff_base: float = Field(default=1.0)
    max_backoff: float = Field(default=64.0)

    # Simulation Speed - Tempi di delay tra iterazioni
    decade_delay_seconds: float = Field(
        default=3.0
    )  # Delay tra decadi (default: 3 secondi)
    annual_event_delay: float = Field(
        default=0.5
    )  # Delay tra eventi annuali (default: 0.5 secondi)
    enable_slow_mode: bool = Field(default=False)  # Modalita lenta per debugging

    # Crisis Thresholds
    crisis_economy_threshold: float = Field(default=0.20)
    crisis_military_threshold: float = Field(default=0.15)
    crisis_political_stability: float = Field(default=0.20)
    crisis_political_legitimacy: float = Field(default=0.10)
    crisis_corruption_max: float = Field(default=0.90)

    # Debate Convergence
    convergence_confidence_threshold: float = Field(default=0.70)
    convergence_disagreement_threshold: float = Field(default=0.20)

    # Checkpoint
    checkpoint_interval_decades: int = Field(default=10)

    # Paths
    data_dir: str = Field(default="./data")
    prompts_dir: str = Field(default="./src/core/prompts")
    reports_dir: str = Field(default="./data/reports")
    checkpoints_dir: str = Field(default="./data/checkpoints")

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
