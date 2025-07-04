"""
Configuration for sphinx
"""
import os
import sys

print(os.getcwd())

sys.path.insert(0, 'bardolph/controller')
sys.path.insert(0, 'bardolph/fakes')
sys.path.insert(0, 'bardolph/lib')
sys.path.insert(0, 'bardolph/parser')
sys.path.append('.')
from bardolph.pygments import bardolph_lexer

project = 'Bardolph'
copyright = '2025, Bardolph Automation, Inc'
author = 'Al Fontes'

from sphinx.highlighting import lexers
lexers ['lightbulb'] = bardolph_lexer.BardolphLexer()
extensions = []

templates_path = ['_templates']

exclude_patterns = []

root_doc = 'contents'
html_favicon = 'www/logo_ico.png'
html_static_path = ['web/static']
html_theme = 'sphinx_rtd_theme'
html_theme_options = {
    'analytics_id': 'G-7VQPMY58X8'
}
