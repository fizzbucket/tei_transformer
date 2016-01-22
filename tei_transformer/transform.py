import os
import subprocess
import hashlib
import shutil
import filecmp
import re

from .xmltotext import Transform


class TransformToPDF():
    
    def __init__(self, inname, outname=None, force=False, quiet=False):
        self.inname = inname
        self.basename = self.inname[:self.inname.find('.')]
        self.working_directory = os.path.join(os.curdir, 'working_directory')
        self.outtex = os.path.join(self.working_directory, self.basename + '.tex')
        if not outname:
            self.outname = self.basename + '.pdf'
        else:
            self.outname = outname
        self.force = force
        self.quiet = quiet
        self.resourcesdir = os.path.join(os.curdir, 'resources')

    def transform(self):
        self.check_requirements()
        latex = self.make_latex()
        pdf_path = self.make_pdf(latex)
        self.on_pdf_creation(pdf_path)

    def check_requirements(self):
        if not os.path.exists(self.working_directory):
            os.mkdir(self.working_directory)

        resource_files = ['references.bib',
                      'personlist.xml',
                      'introduction.tex',
                      'latex_preamble.tex']
        for name in resource_files:
            inp = os.path.join(self.resourcesdir, name)
            outp = os.path.join(self.working_directory, name)
            assert os.path.isfile(inp)

            no_out = not os.path.isfile(outp)
            if no_out:
                self._copy_required_file(inp, outp)
            elif not filecmp.cmp(inp, outp):
                self._copy_required_file(inp, outp)

        i_s_p = os.path.join(self.working_directory, self.basename + '.mst')
        if not os.path.isfile(i_s_p):
            with open(i_s_p, 'w') as isty:
                isty.write(self.index_style())


    def _copy_required_file(self, in_, out_):
        shutil.copy2(in_, out_)
        self.force = True
        if os.path.basename(in_) == 'personlist.xml':
            picklepath = os.path.join(self.working_directory,
                                'personlist.pickle')
            if os.path.isfile(picklepath):
                os.unlink(picklepath)


    def make_latex(self):
        t = self._get_transformer()
        text = t()
        pre = self.latex_preamble()
        front = self.latex_front_matter()
        after = self.latex_end_matter()

        header = pre.replace(r'\begin{document}', front)
        _all = '\n'.join([header, text, after])

        return self._after_creation(_all)

    def make_pdf(self, tex):
        if not self.check_run(tex):
            with open(self.outtex, 'w') as o:
                o.write(tex)
            result = self.call_latex()
        else:
            print('Has not changed since the last run')
        return os.path.join(self.working_directory, self.basename + '.pdf')        

    def on_pdf_creation(self, pdfpath):
        shutil.copy(pdfpath, self.outname)

    def _get_transformer(self):
        transformer = Transform(self.inname, self.working_directory)
        return transformer.transform

    def check_run(self, tex):
        if not self.force:
            if os.path.exists(self.outtex):
                with open(self.outtex, 'rb') as exists:
                    exists = exists.read()
                existing_hash = hashlib.md5(exists).digest()
                new_hash = hashlib.md5(tex.encode('utf8')).digest()
                return existing_hash == new_hash
        return False


    def latex_front_matter(self):
        return '\n'.join([
            '\\begin{document}',
            '\\frontmatter',
            '\\tableofcontents',
            '\setcounter{secnumdepth}{-2}',
            #'\include{./introduction}',
            '\mainmatter',
            '\lineation{page}',
            '\setlength{\stanzaindentbase}{30pt}',
            '\setstanzaindents{3,1,1}',
            '\setcounter{stanzaindentsrepetition}{1}',
            '\\newcommand*{\startstanzahook}{\\vspace{9pt}}',
            '\def\endstanzaextra{\\vspace{9pt}}',
            #'\\allsectionsfont{\\normalsize}',
            '\\beginnumbering',
        ])


    def latex_preamble(self):
        prefile = os.path.join(self.working_directory, 'latex_preamble.tex')
        with open(prefile) as r:
            return r.read()

    def latex_end_matter(self):
        return '\n'.join([
            '\endnumbering',
            '\\backmatter'
            '\clearpage',
            #'\\rfoot{\\textsc{References} / \\thepage}',
            '\printbibliography',
            '\clearpage',
            #'\\rfoot{\\textsc{Editorial Practice} / \\thepage}',
            #'\\rfoot{\\textsc{Index / \\thepage}}',
            '\printindex',
            '\end{document}',
        ])


    def _after_creation(self, text):
        for k, v in {
            'i.e. ': 'i.e.\ ',
            'e.g. ': 'e.g.\ ',
            ' v. ': ' v.\ ',
            ' w. ': ' w.\ ',
            ' wh. ': ' wh.\ ',
            'MG. ': 'MG.\@ ',
            'HQ. ': 'HQ.\@ ',
            'YMCA. ': 'YMCA.\@ ',
            'ADS. ': 'ADS.\@ ',
            'RMT. ': 'RMT.\@ ',
            'NZ. ': 'NZ.\@ ',
            'M.T. ': 'M.T.\@ ',
            'Horowhenua': 'Horo\-whenua',
            'HQ. C.O.': 'HQ.\@ C.O.',
            'C.O. Battalion dinner': 'C.O.\@ Battalion dinner',
            'GA. So': 'GA.\@ So',
            'Trémouille': 'Tré\-mouille',
            'or M&V.': 'or M\\&V.',
            '∴': '\\texttherefore{}', 
        }.items():
            text = text.replace(k, v)
        for char in '.,!)':
            text = text.replace('-' + char, '---' + char)
        hyphensubs = [(r'(?<=\d)-(?=\d)', '--'), # hyphens between numbers to en-dashes
                    (r'(?<=\s)-(?=\s)', '---'), # hyphens surrounded by whitespace to em-dashes.
                    ]
        for sub in hyphensubs:
            text = re.sub(sub[0], sub[1], text)
        # Hyphens in our citations!
        text = re.sub(r'\\pageref\{(.*?)--(.*?)\}',
            r'\\pageref{\1-\2}', text)
        text = re.sub(r'\\autocite\{(.*?)--(.*?)\}',
            r'\\autocite{\1-\2}', text)
        text = re.sub(r'\\label\{(.*?)--(.*?)\}',
            r'\\label{\1-\2}', text)
        text = text.replace('----)', '--)')
        text = re.sub(r'\ +', ' ', text) # Be a tidy kiwi.
        text = re.sub(r'\n\ +', '\n', text)
        text = re.sub(r'\n\n+', '\n\n', text)
        return text


    def index_style(self):
        return '\n'.join(['headings_flag 1',
            'heading_prefix "{\\\\bfseries "',
            'heading_suffix "}\\\\nopagebreak\\n"',
            ])

    def call_latex(self):
        options = ['-bibtex', # run biber for references
           '-cd', # change to working_directory to run
           '-f', # force through errors
           '-g', # run even if unchanged.
           '-pdf',]
        latexmk_command = ['latexmk'] + options + [self.outtex]
        if self.quiet:
            with open(os.devnull, "w") as fnull:
                return subprocess.call(latexmk_command, stdout = fnull, stderr = fnull)
        return subprocess.call(latexmk_command)