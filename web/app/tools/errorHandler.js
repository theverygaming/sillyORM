import { Component, useState, onError } from "@odoo/owl";


export class ErrorHandler extends Component {
    static template = "error_handler"

    setup() {
        this.state = useState({error: false });
        onError(function() {
            this.state.error = true;
        });
    }
}
