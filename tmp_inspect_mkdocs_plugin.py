import inspect
from mkdocs_static_i18n.plugin import I18n
print(inspect.signature(I18n.__init__))
print(I18n.__doc__)
