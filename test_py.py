from flask import Flask
app = Flask(__name__)

@app.route('/')
def hola():
    return "Hola mundo! La app funciona!"

if __name__ == '__main__':
    print("="*50)
    print("Servidor iniciado en http://127.0.0.1:5000")
    print("="*50)
    app.run(debug=True)