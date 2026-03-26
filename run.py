from __future__ import annotations

import argparse

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(description="ATS Hackathon bot runner")
    parser.add_argument(
        "channel",
        choices=["telegram", "discord", "api"],
        help="Which service to run",
    )
    parser.add_argument("--host", default="0.0.0.0", help="API host (for api mode)")
    parser.add_argument("--port", type=int, default=8000, help="API port (for api mode)")
    args = parser.parse_args()

    if args.channel == "telegram":
        from ats_bot.bots.telegram_bot import run_telegram_bot

        run_telegram_bot()
    elif args.channel == "discord":
        from ats_bot.bots.discord_bot import run_discord_bot

        run_discord_bot()
    else:
        uvicorn.run("ats_bot.api:app", host=args.host, port=args.port, reload=False)


if __name__ == "__main__":
    main()
