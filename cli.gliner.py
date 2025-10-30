from app import app
if __name__ == "__main__":
    print("=== URL MAP ===")
    print(app.url_map)
    print("===============")
    app.run(host="0.0.0.0", port=8080, debug=True)
