import { Component, useState, App, loadFile, whenReady } from "@odoo/owl";
import { Counter } from "@counter/counter";
import { ErrorHandler } from "@tools/errorHandler"


class Root extends Component {
    static components = { ErrorHandler, Counter };
    static template = "root"

    setup() {
        this.state = useState({ total: 0 });
    }

    addTotal(amount) {
        this.state.total += amount;
    }
}

const templates = await Promise.all([
    loadFile("templates.xml"),
]);

await whenReady()

const rootApp = new App(Root, { name: "Owl App" });
for (const template of templates) {
    rootApp.addTemplates(template);
}

await rootApp.mount(document.body);

window.onerror = function(msg, url, line, col, error) {
    console.log("error", msg, url, line, col, error);
};
