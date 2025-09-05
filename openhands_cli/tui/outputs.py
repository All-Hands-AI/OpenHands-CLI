# class CustomDiffLexer(Lexer):
#     """Custom lexer for the specific diff format."""

#     def lex_document(self, document: Document) -> StyleAndTextTuples:
#         lines = document.lines

#         def get_line(lineno: int) -> StyleAndTextTuples:
#             line = lines[lineno]
#             if line.startswith("+"):
#                 return [("ansigreen", line)]
#             elif line.startswith("-"):
#                 return [("ansired", line)]
#             elif line.startswith("[") or line.startswith("("):
#                 # Style for metadata lines like [Existing file...] or (content...)
#                 return [("bold", line)]
#             else:
#                 # Default style for other lines
#                 return [("", line)]

#         return get_line
