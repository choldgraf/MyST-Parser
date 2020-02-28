from textwrap import dedent

import pytest

from mistletoe.block_token import tokenize

from myst_parser import text_to_tokens, render_tokens, parse_text
from myst_parser.html_renderer import HTMLRenderer


@pytest.fixture
def renderer():
    renderer = HTMLRenderer()
    with renderer:
        yield renderer


def test_render_tokens():
    root = text_to_tokens("abc")
    assert render_tokens(root, HTMLRenderer) == "<p>abc</p>\n"


def test_front_matter(renderer):
    output = renderer.render(text_to_tokens("---\na: 1\nb: 2\nc: 3\n---"))
    assert output.splitlines() == [
        '<div class="myst-front-matter"><pre><code class="language-yaml">a: 1',
        "b: 2",
        "c: 3",
        "</code></pre></div>",
    ]


def test_front_matter_pygments(renderer, file_regression):
    output = parse_text("---\na: 1\nb: 2\nc: 3\n---", "html", use_pygments=True)
    file_regression.check(output, extension=".html")


def test_block_break(renderer):
    output = renderer.render(text_to_tokens("+++ abc"))
    assert output.splitlines() == [
        "<!-- myst-block-data abc -->",
        '<hr class="myst-block-break" />',
    ]


def test_math(renderer):
    output = renderer.render(tokenize(["$a=1$"])[0])
    assert output == dedent("<p>$$a=1$$</p>")


def test_line_comment(renderer):
    output = renderer.render(tokenize([r"% abc"])[0])
    assert output == "<!-- abc -->"


def test_line_comment_show():
    renderer = HTMLRenderer(show_comments=True)
    with renderer:
        output = renderer.render(tokenize([r"% abc"])[0])
    assert output == '<div class="myst-block-comment"><p>% abc</p></div>'


def test_target():
    output = parse_text("(a)=", "html")
    assert output == (
        '<p><a class="myst-target" href="#a" title="Permalink to here">(a)=</a></p>\n'
    )


def test_role(renderer):
    output = renderer.render(tokenize(["{name}`content`"])[0])
    assert output == (
        '<p><span class="myst-role">'
        '<span class="myst-role-name">{name}</span>'
        '<span class="myst-role-content">&#39;content&#39;</span>'
        "</span></p>"
    )


def test_directive(renderer, file_regression):
    output = renderer.render(tokenize(["```{name} arg\n", "foo\n", "```\n"])[0])
    file_regression.check(output, extension=".html")


def test_minimal_html_page(file_regression):
    # TODO test_minimal_html
    in_string = dedent(
        """\
        ---
        a: 1
        ---
        (title-target)=

        # title

        Abc $a=1$ {role}`content`

        +++ my break

        ```{directive} args
        :option: 1
        content
        ```

        ```python
        def func(a):
            print("{}".format(a))
        ```

        % a comment

        [link to target](#title-target)

        """
    )
    pygments_css = dedent(
        """\
        .highlight  { background: #f8f8f8; }
        .highlight .k { color: #008000; font-weight: bold } /* Keyword */
        .highlight .nf { color: #0000FF } /* Name.Function */
        .highlight .nb { color: #008000 } /* Name.Builtin */
        .highlight .o { color: #666666 } /* Operator */
        .highlight .s2 { color: #BA2121 } /* Literal.String.Double */
        .highlight .si { color: #BB6688; font-weight: bold } /* Literal.String */
        .highlight .nt { color: #008000; font-weight: bold } /* Name.Tag */
        """
    )

    out_string = parse_text(
        in_string,
        "html",
        add_mathjax=True,
        show_comments=True,
        show_front_matter=True,
        use_pygments=True,
        as_standalone=True,
        pygments_css=pygments_css,
    )
    file_regression.check(out_string, extension=".html")
