KINDLEGEN := kindlegen
PYTHON    := python

.DELETE_ON_ERROR:

lsj.prc: lsj.opf dict.html
	$(KINDLEGEN) -c2 -dont_append_source -verbose -o $@ $< 

dict.html: lsj.xml.gz morph.xml.gz create.py beta2unicode.py
	$(PYTHON) create.py $@ lsj.xml.gz morph.xml.gz

CLEAN_FILES := littre.prc dict.html

.PHONY: clean
clean:
	@rm -rf $(GEN_FILES)
