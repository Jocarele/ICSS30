#include "crow_all.h"
#include <vector>

int main() {
    crow::SimpleApp app;

    CROW_ROUTE(app, "/")([]() {
        auto page = crow::mustache::load("index.html");
        return page.render();
    });

   

    std::cout << "Servidor em contato com os feras  http://localhost:8080" << std::endl;
    app.port(8080).multithreaded().run();
}