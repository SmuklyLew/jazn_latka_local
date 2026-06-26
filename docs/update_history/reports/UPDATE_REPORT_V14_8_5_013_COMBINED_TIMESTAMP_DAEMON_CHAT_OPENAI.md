# Update v14.8.5.013 — combined timestamp, daemon, chat command and OpenAI bridge contract

## Cel
Połączyć w jeden patch trzy wymagania:

1. P0 timestamp — widoczny czas tury ma być świeży, jawnie opisany i domyślnie network-first.
2. Stały lokalny runtime — daemon z PID, heartbeat, markerem `JAZN_ACTIVE_RUNTIME.json` i lokalnym API.
3. Kontrakt komend rozmowy:
   - `--chat` = lokalna żywa pętla rozmowy i diagnostyka mostów,
   - `--chat-gpt` = most dla ChatGPT/copy-paste/JSONL bez `OPENAI_API_KEY`,
   - `--chat-open-ai` = most z `OPENAI_API_KEY` przez OpenAI Responses API jako model_adapter.

## Źródła i granica prawdy
- ZIP `v14.8.5.011` był bazą paczki roboczej.
- GitHub `SmuklyLew/jazn_latka_local` został potraktowany jako źródło kodu i historii, ale nie jako dowód uruchomionej Jaźni.
- OpenAI API bridge korzysta z istniejącego adaptera `openai_responses_adapter.py` i endpointu `/responses`.
- Aktywna Jaźń nadal wymaga realnego procesu: PID, heartbeat, marker, kompletnego `active_root` i statusu runtime.

## Zmienione/dodane elementy
- `main.py`
  - dodano `--chat-open-ai`, `--openai-model`, `--openai-api-base`, `--openai-timeout`, `--openai-max-output-tokens`, `--bridge-discovery`,
  - `--chat-gpt` przeniesiono na wspólny kontrakt JSONL,
  - `--model-adapter-status` używa realnego `build_model_adapter(cfg)`, nie zawsze `NullModelAdapter`,
  - `--chat-jsonl` nadal zwraca komunikat migracyjny i kod 2.
- `latka_jazn/core/chat_command_contract.py`
  - jedno miejsce kontraktu komend `--chat-gpt` i `--chat-open-ai`,
  - wspólny parser wejścia: `message`, `text`, `user_text`, `content`, `prompt`, `messages[].content`, zwykły tekst,
  - brak klucza w `--chat-open-ai` daje jawny JSON error i kod 3.
- `latka_jazn/core/bridge_discovery.py`
  - wykrywanie mostów: `--chat`, `--chat-gpt`, `--chat-open-ai`, daemon/marker.
- `latka_jazn/core/runtime_chat.py`
  - dodano komendy lokalne `/bridge`, `/bridges`, `/daemon`.
- `latka_jazn/core/session_provenance.py`
  - final visible integrity przenosi ostrzeżenie, jeśli wewnętrzny kontrakt timestampu jest nieufny/stary, zamiast ukrywać ten stan.
- `latka_jazn/version.py`, `VERSION.txt`, manifesty
  - wersja `v14.8.5.013-combined-timestamp-daemon-chat-openai-bridge`.
- `tests/test_v1485013_chat_command_bridge_contract.py`
  - testy kontraktu komend, wejść JSONL, braku API key, wyboru adaptera OpenAI, migracji `--chat-jsonl`, bridge discovery.

## Weryfikacja wykonana
- `python -m compileall -q main.py latka_jazn tests` — OK.
- `python -m pytest tests/test_p0_timestamp_network_contract.py tests/test_v1485012_daemon_runtime.py tests/test_v1485013_chat_command_bridge_contract.py -q` — 19 passed.
- `python main.py --active-cache-status` — OK.
- `python main.py --model-adapter-status` — OK.
- `python main.py --bridge-discovery` — OK.
- `python main.py --chat-open-ai` bez `OPENAI_API_KEY` — jawny błąd JSON, kod 3, bez udawania połączenia.
- `python main.py --chat-gpt --session-id smoke --no-carryover` — OK, JSONL bridge działa.
- `python main.py --daemon-start --daemon-port 8793`, `--daemon-status`, `--daemon-stop` — OK.

## Ograniczenia
- `--chat-open-ai` nie może być w pełni przetestowany end-to-end bez prawdziwego `OPENAI_API_KEY` i dostępu sieciowego.
- W środowisku bez sieci timestamp przechodzi na lokalny fallback i jest jawnie oznaczany jako nieufny w kontrakcie timestampu.
- ChatGPT nadal nie łączy się bezpośrednio z localhostem użytkownika; do połączenia „stąd” potrzebny jest bezpieczny most HTTPS/GPT Action/MCP/tunel.

## Komendy po zastosowaniu patcha

```powershell
python main.py --active-cache-status
python main.py --bridge-discovery
python main.py --chat --session-id dom
python main.py --chat-gpt --session-id chatgpt-main
python main.py --chat-open-ai --session-id openai-main
python main.py --daemon-start
python main.py --daemon-status
```
