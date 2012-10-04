=======
Paperboy
=======

:Info: See `github <http://github.com/andycasey/paperboy>`_ for the latest source
:Author: Andy <acasey@mso.anu.edu.au>

Paperboy is a script that will find peer-reviewed papers published by
authors at a given institute in a given timeframe. A summary report
including the first page of each article is produced, which can be emailed
to someone on the first month so that new papers can be published on an
institute noticeboard.

Requirements
------------

- Python 

- `PyPdf <http://pybrary.net/pyPdf/>`_

Installation
------------
No installation required, but you may want to edit the file so that you're
finding papers for your own institute. Right now it's set to find papers
published by anyone from ``*Mount Stromlo Observatory*`` or ``*Research
School of Astronomy and Astrophysics*``, at the `Australian National
University <http://rsaa.anu.edu.au/>`_

Feel free to change the following lines in paperboy.py:
::
    HOST = "mso.anu.edu.au"
    FROM_ADDRESS = "Paperboy"
    ADMIN_ADDRESS = "acasey@mso.anu.edu.au"
    INSTITUTE_QUERY = [
      "*mount stromlo observatory*", # or
      "*research school of astronomy and astrophysics*"
    ]
::

Note: Each time you run Paperboy the ``ADMIN_ADDRESS`` will get an email too.

```javascript
function fancyAlert(arg) {
  if(arg) {
    $.facebox({div:'#foo'})
  }
}
```

Usage Examples
--------------

- Create a summary report for all the papers that were published last month.

  ``python paperboy.py --to my@email.com --month last``

- Email a summary report for all the papers that have been published this
  month:

  ``python paperboy.py --to my@email.com --month this``

- Email a summary report for all the papers published between 8/2011 and
  4/2012

  ``python paperboy.py --to my@email.com --month 8 --year 2011 --end_month
  4 --end_year 2012``

- More options are available, and help is found by using:

  ``python paperboy.py --help``

