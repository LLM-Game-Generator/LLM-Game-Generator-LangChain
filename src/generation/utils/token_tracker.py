import time
import contextlib
from langchain_core.callbacks import BaseCallbackHandler


class TokenTrackerCallback(BaseCallbackHandler):
    def __init__(self):
        # Overall statistics
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.one_time_token_usage = 0

        # System-level time statistics
        self.system_start_time = time.time()
        self.total_llm_time = 0.0

        # Track start time for each LLM request
        self.active_runs = {}

        # Grouped (Agent/Step) statistics
        self.step_usage = {}
        self._current_step = "System"  # Default tag
        self._init_step_dict(self._current_step)

    def _init_step_dict(self, step_name: str):
        """Initialize the statistics dictionary for a specific step."""
        if step_name not in self.step_usage:
            self.step_usage[step_name] = {
                "prompt": 0,
                "completion": 0,
                "total": 0,
                "max_single": 0,
                "step_time": 0.0,  # Total time spent on the entire Node/Step (including image gen, RAG)
                "llm_time": 0.0  # Pure LLM generation wait time
            }

    @property
    def total_tokens(self):
        return self.prompt_tokens + self.completion_tokens

    @property
    def one_time_max_token_usage(self):
        return self.one_time_token_usage

    @contextlib.contextmanager
    def track_step(self, step_name: str):
        """
        Context manager.
        Used to track Token usage and total execution time for a specific Agent.
        """
        previous_step = self._current_step
        self._current_step = step_name
        self._init_step_dict(step_name)

        # Record step start time
        step_start_time = time.time()
        try:
            yield
        finally:
            # Calculate total time spent on the step
            elapsed = time.time() - step_start_time
            self.step_usage[step_name]["step_time"] += elapsed
            self._current_step = previous_step

    def set_current_step(self, step_name: str):
        """Simple Setter (if not using the 'with' statement)."""
        self._current_step = step_name
        self._init_step_dict(step_name)

    def on_llm_start(self, serialized, prompts, **kwargs):
        """Triggered when LLM starts generating, records pure LLM start time."""
        run_id = kwargs.get("run_id")
        if run_id:
            self.active_runs[run_id] = time.time()

    def on_llm_end(self, response, **kwargs):
        """Triggered when LLM finishes generating, calculates Token usage and pure LLM time."""

        # --- Calculate pure LLM time ---
        run_id = kwargs.get("run_id")
        llm_elapsed = 0.0
        if run_id and run_id in self.active_runs:
            llm_elapsed = time.time() - self.active_runs.pop(run_id)
            self.total_llm_time += llm_elapsed

        counted = False
        prompt_tokens = 0
        completion_tokens = 0

        # --- Calculate Tokens ---
        if response.generations:
            for gen_list in response.generations:
                for gen in gen_list:
                    if (hasattr(gen, "message") and
                            hasattr(gen.message, "usage_metadata") and
                            gen.message.usage_metadata):
                        usage = gen.message.usage_metadata
                        prompt_tokens += usage.get("input_tokens", 0)
                        completion_tokens += usage.get("output_tokens", 0)
                        counted = True

        if (not counted and
                response.llm_output and
                "token_usage" in response.llm_output):
            usage = response.llm_output["token_usage"]
            prompt_tokens += usage.get("prompt_tokens", 0)
            completion_tokens += usage.get("completion_tokens", 0)

        current_total = prompt_tokens + completion_tokens

        # --- Update overall statistics ---
        if self.one_time_token_usage < current_total:
            self.one_time_token_usage = current_total

        self.prompt_tokens += prompt_tokens
        self.completion_tokens += completion_tokens

        # --- Update current Agent (Step) statistics ---
        self._init_step_dict(self._current_step)
        stats = self.step_usage[self._current_step]

        stats["prompt"] += prompt_tokens
        stats["completion"] += completion_tokens
        stats["total"] += current_total
        stats["llm_time"] += llm_elapsed

        if stats["max_single"] < current_total:
            stats["max_single"] = current_total

    def print_summary(self, log_callback=print):
        """Print detailed Token usage report and performance analysis."""
        log_callback("\n" + "=" * 60)
        log_callback(f"{'[Token & Performance Report]':^60}")
        log_callback("=" * 60)

        # Sequentially print the cost for each Agent
        for step, stats in self.step_usage.items():
            if stats["total"] > 0 or stats["step_time"] > 0:
                step_time = stats["step_time"]
                llm_time = stats["llm_time"]
                # Use pure LLM time to calculate accurate TPS
                tps = stats["completion"] / llm_time if llm_time > 0 else 0.0

                log_callback(f"[{step.upper()}]")
                log_callback(f"  Prompt (Input) : {stats['prompt']:>8}")
                log_callback(f"  Completion     : {stats['completion']:>8}")
                log_callback(f"  Total Tokens   : {stats['total']:>8}")
                log_callback(f"  Max Single     : {stats['max_single']:>8}")
                log_callback(f"  Step Duration  : {step_time:>8.2f} s")
                log_callback(f"  LLM Wait Time  : {llm_time:>8.2f} s")
                log_callback(f"  LLM Tokens/Sec : {tps:>8.2f} t/s")
                log_callback("-" * 60)

        # Overall system statistics
        system_elapsed = time.time() - self.system_start_time
        overall_tps = self.completion_tokens / self.total_llm_time if self.total_llm_time > 0 else 0.0

        log_callback("[OVERALL SYSTEM]")
        log_callback(f"  Total Prompt   : {self.prompt_tokens:>8}")
        log_callback(f"  Total Output   : {self.completion_tokens:>8}")
        log_callback(f"  GRAND TOTAL    : {self.total_tokens:>8}")
        log_callback(f"  Sys Max Single : {self.one_time_max_token_usage:>8}")
        log_callback(f"  Total Time     : {system_elapsed:>8.2f} s")
        log_callback(f"  Total LLM Time : {self.total_llm_time:>8.2f} s")
        log_callback(f"  Avg LLM TPS    : {overall_tps:>8.2f} t/s")
        log_callback("=" * 60 + "\n")