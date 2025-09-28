from flask import Flask

app = Flask(__name__)

@app.route("/")
def hello():
	return "Baraa"

if __name__ == "__main__":
	app.run(debug=false,host="0.0.0.0")