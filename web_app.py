from flask import Flask

app = Flask(__name__)


@app.get("/")
def hello():
    return "Hello, World!"


def main() -> None:
    app.run(host="127.0.0.1", port=5000, debug=False)


if __name__ == "__main__":
    main()
