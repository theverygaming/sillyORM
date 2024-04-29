import { Component, useState } from "@odoo/owl";


export class Counter extends Component {
    static template = "counter";

    setup() {
        this.state = useState({ count: 0 });
    }

    add(amount) {
        this.state.count += amount;
        if (this.props.callback) {
            this.props.callback(amount);
        }
    }

    increment() {
        this.add(1);
    }

    decrement() {
        this.add(-1);
    }
}
