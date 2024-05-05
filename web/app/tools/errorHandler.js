import { Component, useState, onError } from "@odoo/owl";


export class ErrorHandler extends Component {
    static template = "error_handler"

    setup() {
        this.state = useState({error: false });
        onError(function(error) {
            console.log(error);
            this.state.error = true;
        });
    }
}
