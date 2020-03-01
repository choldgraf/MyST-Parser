import html
from itertools import chain
import pkg_resources
import re
from textwrap import dedent

from mistletoe import block_token, span_token
from mistletoe import html_renderer

from myst_parser import span_tokens as myst_span_tokens
from myst_parser import block_tokens as myst_block_tokens
from myst_parser import static


class HTMLRenderer(html_renderer.HTMLRenderer):
    def __init__(
        self,
        add_mathjax=False,
        show_comments=False,
        show_front_matter=True,
        use_pygments=False,
        as_standalone=False,
        myst_css=None,
        pygments_css=None,
    ):
        """This HTML render uses the same block/span tokens as the docutils renderer.

        It is used to test compliance with the commonmark spec.
        """
        self.show_comments = show_comments
        self.show_front_matter = show_front_matter
        self.myst_css = myst_css
        self.use_pygments = use_pygments
        self.pygments_css = pygments_css
        self.add_mathjax = add_mathjax
        self.as_standalone = as_standalone

        self._suppress_ptag_stack = [False]

        _span_tokens = self._tokens_from_module(myst_span_tokens)
        _block_tokens = self._tokens_from_module(myst_block_tokens)

        super(html_renderer.HTMLRenderer, self).__init__(
            *chain(_block_tokens, _span_tokens)
        )

        span_token._token_types.value = _span_tokens
        block_token._token_types.value = _block_tokens

        # html.entities.html5 includes entitydefs not ending with ';',
        # CommonMark seems to hate them, so...
        self._stdlib_charref = html._charref
        _charref = re.compile(
            r"&(#[0-9]+;" r"|#[xX][0-9a-fA-F]+;" r"|[^\t\n\f <&#;]{1,32};)"
        )
        html._charref = _charref

    def render_document(self, token):
        """
        Optionally Append CDN link for MathJax to the end of <body>.
        """
        body = super().render_document(token)
        if self.add_mathjax:
            body += (
                "<script src="
                '"https://cdnjs.cloudflare.com/ajax/libs/mathjax/2.7.0/MathJax.js'
                '?config=TeX-MML-AM_CHTML"></script>\n'
            )
        if not self.as_standalone:
            return body
        css = get_syntax_css() if self.myst_css is None else self.myst_css
        if self.use_pygments:
            css += (
                get_pygments_css() if self.pygments_css is None else self.pygments_css
            )
        return minimal_html_page(body, css=css)

    def render_block_code(self, token):
        if (not token.language) or (not self.use_pygments):
            return super().render_block_code(token)
        highlighted = pygments_highlight(token.children[0].content, token.language)
        if highlighted is None:
            # language not found
            return super().render_block_code(token)
        return "\n".join(
            [
                '<div class="highlight-{}">'.format(token.language),
                highlighted.rstrip(),
                "</div>",
            ]
        )

    def render_code_fence(self, token):
        if token.language and token.language.startswith("{"):
            return self.render_directive(token)
        return self.render_block_code(token)

    def render_directive(self, token):
        # TODO use drop-down?
        # <details open>
        # <summary>{name} args</summary>
        # options
        # content
        # </details>
        return (
            '<div class="myst-directive">'
            "{t}{t}{t}"
            '<span class="myst-dir-name">{name}</span>&nbsp\n'
            '<span class="myst-dir-args">{args}</span>\n'
            '<span class="myst-dir-content"><pre><code>{content}</code></pre></span>\n'
            "{t}{t}{t}"
            "</div>"
        ).format(
            t="&#39;",
            name=token.language,
            args=token.arguments,
            content=token.children[0].content,
        )

    def render_front_matter(self, token):
        if not self.show_front_matter:
            return ""
        if self.use_pygments:
            highlighted = pygments_highlight(token.content, "yaml")
            return '<div class="highlight-yaml myst-front-matter">\n{}\n</div>'.format(
                highlighted.rstrip()
            )
        return (
            '<div class="myst-front-matter">'
            '<pre><code class="language-yaml">{}</code></pre>'
            "</div>"
        ).format(self.escape_html(token.content))

    def render_line_comment(self, token):
        if not self.show_comments:
            return "<!-- {} -->".format(self.escape_html(token.content))
        return '<div class="myst-block-comment"><p>{}</p></div>'.format(
            self.escape_html(token.raw)
        )

    def render_block_break(self, token):
        return '<!-- myst-block-data {} -->\n<hr class="myst-block-break" />'.format(
            self.escape_html(token.content)
        )

    def render_target(self, token):
        return (
            '<a class="myst-target" href="#{0}" title="Permalink to here">({0})=</a>'
        ).format(self.escape_html(token.target))

    def render_role(self, token):
        return (
            '<span class="myst-role">'
            '<span class="myst-role-name">{{{name}}}</span>'
            '<span class="myst-role-content">{tick}{content}{tick}</span>'
            "</span>"
        ).format(
            name=token.name,
            content=self.render_raw_text(token.children[0]),
            # TODO I use apostrophe rather than ticks here because ticks
            # make the text italic (at least in my browser)
            tick="&#39;",
        )

    def render_math(self, token):
        """Ensure Math tokens are all enclosed in two dollar signs."""
        if token.content.startswith("$$"):
            return self.render_raw_text(token)
        return "${}$".format(self.render_raw_text(token))


def pygments_highlight(code: str, language: str):
    from pygments import highlight
    from pygments.formatters import HtmlFormatter
    from pygments.lexers import get_lexer_by_name
    from pygments.util import ClassNotFound

    try:
        return highlight(code, get_lexer_by_name(language), HtmlFormatter())
    except ClassNotFound:
        return None


def get_pygments_css():
    from pygments.formatters import HtmlFormatter

    return HtmlFormatter().get_style_defs(".highlight")


def minimal_html_page(
    body: str, css: str = "", title: str = "Standalone HTML", lang: str = "en"
):
    return dedent(
        """\
    <!DOCTYPE html>
    <html lang="{lang}">

    <head>
    <meta charset="utf-8">
    <title>{title}</title>
    <style>
    {css}
    </style>
    </head>
    <body>
    {body}
    </body>
    </html>
    """
    ).format(title=title, lang=lang, css=css, body=body)


def get_syntax_css():
    return pkg_resources.resource_string(static.__name__, "myst_standalone.css").decode(
        "utf-8"
    )
