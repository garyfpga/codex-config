# subagent
1. always spawn subagent with high effort unless specify otherwise
2. always spawn the same model as main agent unless specify otherwise
3. Exception: when a Simple Power skill or plan specifies subagent dispatch settings, those settings count as "specified otherwise" and override the same-model default. In particular, Simple Power `sp-impl` workers use `model="gpt-5.4-mini"` and `reasoning_effort="high"` unless the user explicitly overrides.
