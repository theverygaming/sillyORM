from lxml import etree


_HTML_SELFCLOSING_TAGS = [
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
    "command",
    "keygen",
    "menuitem",
    "frame",
]

templates = {}

def _render_html(element, render_ctx, render_self=False):
    def f_render_element_beg(render_tag, render_text):
        output = ""
        if render_tag:
            output += f"<{element.tag}" + (" " if len(element.items()) else "")
            for k, v in element.items():
                output += f'{k}="{v}"'
            output += f">"
        if render_text and element.text is not None:
            output += element.text
        return output

    def f_render_children():
        output = ""
        for child in element:
            output += _render_html(child, render_ctx, render_self=True)
        return output

    def f_render_element_end(render_tag, render_tail):
        output = ""
        if render_tag and element.tag not in _HTML_SELFCLOSING_TAGS:
            output += f"</{element.tag}>"
        if render_tail and element.tail is not None:
            output += element.tail
        return output

    def process_attrs(render_tag, render_tail, render_text, render_children):
        output = ""
        for k, v in element.attrib.items():
            # t-att-
            if k.startswith("t-att-"):
                del element.attrib[k]
                element.attrib[k.removeprefix("t-att-")] = render_ctx[v]
                continue
            # t-raw
            if k == "t-raw":
                del element.attrib[k]
                element.text = render_ctx[v]
                continue
            # t-set
            if k == "t-set":
                render_tag = render_text = render_children = False
                render_ctx[v] = element.text if element.text is not None else ""
                render_ctx[v] += f_render_children()
                continue
            # t-call
            if k == "t-call":
                render_tag = render_tail = render_text = render_children = False
                render_ctx["0"] = (element.text if element.text is not None else "") + f_render_children()
                output += _render_html(templates[v], render_ctx)
                continue
            # t-strip
            if k.startswith("t-strip-"):
                del element.attrib[k]
                st = k.removeprefix("t-strip-")
                match st:
                    case "text":
                        element.text = element.text.lstrip(v)
                    case "tail":
                        element.tail = element.tail.rstrip(v)
                    case _:
                        raise Exception(f'invalid {k}="{v}"')
                continue
        return output, render_tag, render_tail, render_text, render_children
    if not isinstance(element.tag, str):
        raise Exception(f"unknown tag {element.tag}")
    render_tag = render_tail = render_self
    render_text = render_children = True
    # we don't render the t tag
    if element.tag == "t":
        render_tag = False
    output, render_tag, render_tail, render_text, render_children = process_attrs(render_tag, render_tail, render_text, render_children)
    output += f_render_element_beg(render_tag, render_text)
    if render_children:
        output += f_render_children()
    output += f_render_element_end(render_tag, render_tail)
    return output

def load_file(fname):
    parser = etree.XMLParser(remove_comments=True)
    tree = etree.parse(fname, parser=parser)
    for el in tree.getroot():
        if el.tag != "template":
            continue
        name = el.attrib.get("name")
        if not name:
            raise Exception("name attribute required for template")
        templates[name] = el

    print(_render_html(templates["test"], {}))
    #print(_render_html(templates["html_base"], {"lang": "en-US", "title": "test", "head": "<script></script>", "body": "<p>hello world!</p>"}))

load_file("test.xml")

#print(_render(tree.getroot()))
#print("\n\n")
#print(etree.tostring(tree.getroot(), encoding="unicode"))
