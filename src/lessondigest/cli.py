from __future__ import annotations

import argparse
import sys
from pathlib import Path

from lessondigest import __version__
from lessondigest.config import AppConfig
from lessondigest.domain import HumanEvaluation
from lessondigest.errors import ConfigError, LessonDigestError
from lessondigest.logging_setup import get_logger, setup_logging
from lessondigest.pipeline import STAGES, Pipeline
from lessondigest.storage import FilesystemStorage
from lessondigest import media

log = get_logger("cli")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lessondigest",
        description="Запись урока → транскрипт → структурированный дайджест",
    )
    parser.add_argument("--version", action="version", version=f"lessondigest {__version__}")
    parser.add_argument("--config", type=Path, default=None, help="Путь к config.yaml")
    parser.add_argument("--verbose", action="store_true", help="Подробные логи")

    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="Обработать аудио урока")
    run.add_argument("--audio", type=Path, default=None, help="Путь к аудиофайлу")
    run.add_argument("--run", dest="run_id", default=None, help="Возобновить существующий run_id")
    run.add_argument("--subject", default=None, help="Предмет (алгебра, физика, ...)")
    run.add_argument("--from", dest="from_stage", choices=("auto", *STAGES), default="auto")
    run.add_argument("--force", action="store_true", help="Пересчитать выбранные этапы")
    run.add_argument("--open", dest="open_result", action="store_true", help="Открыть дайджест")
    run.add_argument("--asr-provider", default=None)
    run.add_argument("--asr-model", default=None)
    run.add_argument("--llm-provider", default=None)
    run.add_argument("--llm-model", default=None)

    sub.add_parser("doctor", help="Проверить окружение и конфиг")

    sub.add_parser("list", help="Список прогонов")

    serve = sub.add_parser("serve", help="Запустить веб-интерфейс")
    serve.add_argument("--host", default="127.0.0.1", help="0.0.0.0 — доступ с телефона по Wi-Fi")
    serve.add_argument("--port", type=int, default=8000)

    evaluate = sub.add_parser("eval", help="Оценить дайджест вручную")
    evaluate.add_argument("--run", dest="run_id", required=True)
    evaluate.add_argument("--usefulness", type=int, choices=range(1, 6), required=True)
    evaluate.add_argument("--homework", choices=("yes", "no", "na"), default="na")
    evaluate.add_argument("--notes", default="")
    evaluate.add_argument("--evaluator", default="")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    setup_logging(verbose=args.verbose)

    try:
        config = AppConfig.load(args.config)
    except LessonDigestError as exc:
        log.error("%s", exc)
        return exc.exit_code

    if args.command == "doctor":
        return _cmd_doctor(config)
    if args.command == "list":
        return _cmd_list(config)

    try:
        if args.command == "run":
            _apply_overrides(config, args)
            return _cmd_run(config, args)
        if args.command == "serve":
            return _cmd_serve(config, args)
        if args.command == "eval":
            return _cmd_eval(config, args)
    except LessonDigestError as exc:
        log.error("%s", exc)
        return exc.exit_code
    except KeyboardInterrupt:
        log.error("Прервано пользователем")
        return 130

    parser.print_help()
    return 1


def _apply_overrides(config: AppConfig, args: argparse.Namespace) -> None:
    if getattr(args, "asr_provider", None):
        config.asr.provider = args.asr_provider
    if getattr(args, "asr_model", None):
        config.asr.model = args.asr_model
    if getattr(args, "llm_provider", None):
        config.llm.provider = args.llm_provider
    if getattr(args, "llm_model", None):
        config.llm.model = args.llm_model


def _cmd_run(config: AppConfig, args: argparse.Namespace) -> int:
    pipeline = Pipeline(config)
    result = pipeline.run(
        audio=args.audio,
        run_id=args.run_id,
        subject=args.subject,
        from_stage=args.from_stage,
        force=args.force,
        open_result=args.open_result,
    )
    if result.skipped_stages:
        log.info("Пропущены этапы: %s", ", ".join(result.skipped_stages))
    for warning in result.warnings:
        log.warning("%s", warning)
    print(f"run_id: {result.run_id}")
    print(f"status: {result.status.value}")
    if result.digest_md:
        print(f"digest: {result.digest_md}")
    return 0


def _cmd_list(config: AppConfig) -> int:
    storage = FilesystemStorage(config.paths)
    runs = storage.list_runs()
    if not runs:
        print("Прогонов нет")
        return 0
    for run_id in runs:
        meta = storage.load_run_meta(run_id)
        print(f"{run_id}\t{meta.status.value}\t{meta.subject}\t{meta.duration_sec or '-'}")
    return 0


def _cmd_serve(config: AppConfig, args: argparse.Namespace) -> int:
    try:
        import uvicorn
    except ImportError as exc:
        raise ConfigError(
            "uvicorn не установлен. Установите веб-зависимости: pip install 'lessondigest[web]'"
        ) from exc
    from lessondigest.web.app import create_app

    app = create_app(config)
    if args.host not in {"127.0.0.1", "localhost"}:
        log.warning("Веб-интерфейс без авторизации доступен в сети по адресу %s:%s", args.host, args.port)
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    return 0


def _cmd_eval(config: AppConfig, args: argparse.Namespace) -> int:
    storage = FilesystemStorage(config.paths)
    homework = {"yes": True, "no": False, "na": None}[args.homework]
    evaluation = HumanEvaluation(
        run_id=args.run_id,
        usefulness_1_to_5=args.usefulness,
        homework_correct=homework,
        notes=args.notes,
        evaluator=args.evaluator,
    )
    path = storage.save_evaluation(evaluation)
    log.info("Оценка сохранена: %s", path)
    _write_eval_summary(storage)
    return 0


def _write_eval_summary(storage: FilesystemStorage) -> None:
    evaluations = storage.list_evaluations()
    if not evaluations:
        return
    scores = [e.usefulness_1_to_5 for e in evaluations if e.usefulness_1_to_5]
    homework_scored = [e for e in evaluations if e.homework_correct is not None]
    homework_ok = [e for e in homework_scored if e.homework_correct]

    lines = ["# Оценки дайджестов", "", f"Всего оценок: {len(evaluations)}", ""]
    if scores:
        lines.append(f"Средняя полезность: {sum(scores) / len(scores):.2f} / 5 (n={len(scores)})")
    if homework_scored:
        lines.append(
            f"Домашка корректна: {len(homework_ok)}/{len(homework_scored)} "
            f"({100 * len(homework_ok) / len(homework_scored):.0f}%)"
        )
    lines += ["", "| run_id | useful | homework | notes |", "|---|---|---|---|"]
    for e in evaluations:
        lines.append(
            f"| {e.run_id} | {e.usefulness_1_to_5 or '-'} | {e.homework_correct} | {e.notes} |"
        )
    storage.paths.digests_eval.mkdir(parents=True, exist_ok=True)
    (storage.paths.digests_eval / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _cmd_doctor(config: AppConfig) -> int:
    print(f"lessondigest {__version__}")
    print(f"project root: {config.paths.root}")
    print(f"audio raw:    {config.paths.audio_raw}")
    print(f"asr:          {config.asr.provider} / {config.asr.model} ({config.asr.device})")
    print(f"llm:          {config.llm.provider} / {config.llm.model}")
    print(f"prompt:       {config.llm.prompt_version} -> {config.prompt_path()}")

    problems: list[str] = []
    print(f"ffmpeg:       {'да' if media.has_ffmpeg() else 'НЕТ (падает в PATH)'}")
    if not media.has_ffmpeg():
        problems.append("ffmpeg/ffprobe не найден: метаданные и нормализация недоступны")

    prompt_ok = config.prompt_path().exists()
    print(f"prompt file:  {'есть' if prompt_ok else 'НЕТ'}")
    if not prompt_ok:
        problems.append(f"нет файла промпта {config.prompt_path()}")

    if config.asr.provider in {"faster_whisper", "faster-whisper", "whisper"}:
        try:
            import faster_whisper  # noqa: F401

            print("faster-whisper: установлен")
        except ImportError:
            print("faster-whisper: НЕ установлен")
            problems.append("faster-whisper не установлен (pip install faster-whisper)")

    if config.llm.provider in {"gigachat", "giga"}:
        have = config.secrets.has_gigachat_credentials()
        print(f"GigaChat keys: {'есть' if have else 'НЕТ'}")
        if not have:
            problems.append("GIGACHAT_CLIENT_ID/SECRET не заданы (см. .env.example)")

    try:
        import fastapi  # noqa: F401
        import uvicorn  # noqa: F401

        print("web deps:     есть")
    except ImportError:
        print("web deps:     НЕТ (pip install 'lessondigest[web]')")

    if config.paths.root.exists():
        try:
            config.paths.ensure()
        except OSError as exc:
            problems.append(f"не удалось создать папки проекта: {exc}")

    if problems:
        print("\nПроблемы:")
        for problem in problems:
            print(f"  - {problem}")
        return 2
    print("\nОк")
    return 0


if __name__ == "__main__":
    sys.exit(main())
