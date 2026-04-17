"""
Entry point — start the API Gateway with uvicorn.
"""
import uvicorn


def main():
    uvicorn.run(
        "the_orchestrator.gateway.app:app",
        host="0.0.0.0",
        port=3300,
        reload=True,
        log_level="info",
    )


if __name__ == "__main__":
    main()
