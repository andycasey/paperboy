#!/usr/local/python-2.7.1/bin/python
# Papyrboy written by Andy Casey (acasey@mso.anu.edu.au) on 14 Jun 2012
# Please contact me before distributing or editing any of this code for uses which it was not intended for.
import logging
from datetime import datetime

logging.basicConfig(filename=datetime.now().strftime('%Y-%m-%d_%H:%M:%S.log'), filemode='w', level=logging.DEBUG)

import os
import re
import urllib2
import smtplib
import sys
import textwrap
import time
import traceback

from calendar import monthrange

from email import Encoders
from email.MIMEBase import MIMEBase
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
from email.Utils import formatdate

from pyPdf import PdfFileReader, PdfFileWriter


def retrieve_article_urls(start_year, start_month, end_year, end_month, timeout=120):
    """Retrieves the bibliography codes and URLS for all peer-reviewed articles
    published in the specified time frame with an affiliation from Mount Stromlo
    Observatory / Research School of Astronomy & Astrophysics, ANU."""
    
    st = datetime(start_year, start_month, 1)
    et = datetime(end_year, end_month, monthrange(end_year, end_month)[1])
    
    if st > et:
        raise ValueError("End date specified is before the start date.")
    
    if st > datetime.now():
        raise ValueError("We're astronomers not astrologers; we can't predict the future.")
    
    
    logging.info("Looking for peer-reviewed articles on ADS published between %i/%i and %i/%i" \
                 % (start_year, start_month, end_year, end_month, ))
    
    # Prepare the data for ADS    
    
    affiliation = "*mount stromlo observatory*\n*research school of astronomy and astrophysics*".replace("\n", "%0D%0A").replace(' ', '+') # TODO be more elegant
    data = 'db_key=AST&db_key=PRE&qform=AST&arxiv_sel=astro-ph&arxiv_sel=cond-mat&arxiv_sel=cs&arxiv_sel=gr-qc&arxiv_sel=hep-ex&arxiv_sel=hep-lat&arxiv_sel=hep-ph&arxiv_sel=hep-th&arxiv_sel=math&arxiv_sel=math-ph&arxiv_sel=nlin&arxiv_sel=nucl-ex&arxiv_sel=nucl-th&arxiv_sel=physics&arxiv_sel=quant-ph&arxiv_sel=q-bio&sim_query=YES&ned_query=YES&adsobj_query=YES&aut_logic=OR&obj_logic=OR&author=&object=&start_mon=%i&start_year=%i&end_mon=%i&end_year=%i&ttl_logic=OR&title=&txt_logic=OR&text=&kwd_logic=OR&keyword=&aff_req=YES&aff_logic=OR&affiliation=%s&nr_to_return=200&start_nr=1&jou_pick=NO&ref_stems=&data_and=ALL&group_and=ALL&start_entry_day=&start_entry_mon=&start_entry_year=&end_entry_day=&end_entry_mon=&end_entry_year=&min_score=&sort=SCORE&data_type=SHORT&aut_syn=YES&txt_syn=YES&txt_syn=YES&aut_wt=1.0&obj_wt=1.0&ttl_wt=0.3&txt_wt=3.0&aut_wgt=YES&obj_wgt=YES&ttl_wgt=YES&txt_wgt=YES&ttl_sco=YES&txt_sco=YES&version=1&aff_syn=NO&aff_wt=1.0&aff_wgt=YES&kwd_sco=YES&kwd_syn=NO&kwd_wt=1.0&kwd_wgt=YES&kwd_sco=YES' \
                % (start_month, start_year, end_month, end_year, affiliation, )
    host = 'http://adsabs.harvard.edu/cgi-bin/nph-abs_connect?' + data
    
    # Perform the query
    request = urllib2.Request(host)
    handle = urllib2.urlopen(request, timeout=timeout)
    data = ''.join(handle.read())
    
    # Search for pre-prints and article links
    
    preprints = re.findall('href="\S+link_type=PREPRINT"', data)
    articles = re.findall('href="\S+link_type=ARTICLE"', data)
    
    logging.info("Identified %i preprint links and %i article links." % (len(preprints), len(articles), ))
    if len(preprints) > len(articles):
        logging.info("Preprint links will be used wherever refereed article files are unavailable.")
    
    # Clean up the links
    preprints = [preprint.split('"')[1] for preprint in preprints]
    articles = [article.split('"')[1] for article in articles]
    
    article_baselinks = [';'.join(article.split(';')[:-1]) for article in articles]
    
    article_urls = []
    
    # Check for any papers that have preprints but no full refereed journal article
    for preprint in preprints:
        link = ';'.join(preprint.split(';')[:-1])
        
        if link not in article_baselinks:
            # This particular paper had no full PDF link, so we will have to take
            # the pre-print
            article_urls.append(preprint)
        
        else:
            # This will maintain chronological order of all the articles
            article_urls.append(articles[article_baselinks.index(link)])
            
    # Clean up the links
    article_urls = [article.replace('&#38;', '&') for article in article_urls] # TODO be more elegant
    
    # Extract bibcodes
    bibcodes = []
    for article in article_urls:
        bibcode = re.findall('(?<=bibcode=)\S+(?=&db_key)', article)
        
        if len(bibcode) is 0:
            logging.warn("Could not find bibliography code from URL (%s). Assigning random string instead." % (article, ))
            bibcode = ''
        else: bibcode = bibcode[0].replace('%26', '&') # TODO be more elegant
        
        bibcodes.append(bibcode)
        
        
    return zip(bibcodes, article_urls)
    



def download_article(article_url, output, clobber=True, timeout=120):
    """Retrieves an article or pre-print PDF from ADS and saves it to disk."""

    if not article_url.startswith('http://adsabs.harvard.edu'):
        raise ValueError('Expected an article URL that from ADS, but the URL did not start with http://adsabs.harvard.edu: "%s"' % (article_url, ))
        
    if os.path.exists(output) and not clobber:
        raise IOError('Filename exists (%s) and we will not clobber it.' % (article_url, ))
    
    logging.info("Attempting to download article from %s" % (article_url, ))
    
    request = urllib2.Request(article_url)
    handle = urllib2.urlopen(request, timeout=timeout)
    
    
    if handle.geturl().startswith('http://arXiv.org/'):
        # This is a pre-print URL, so we actually need to rget the real PDF
        real_article_url = handle.geturl().replace('/abs/', '/pdf/')
        logging.info("This article is a preprint, so we are taking it from %s instead" % (real_article_url, ))
        
        request = urllib2.Request(real_article_url)
        handle = urllib2.urlopen(request, timeout=timeout)
    
    elif handle.geturl().startswith('http://onlinelibrary.wiley.com'):
        # Wiley have this annoying frame that we need to navigate through.
        
        data = handle.read()
        
        real_article_url = re.findall('iframe id="pdfDocument" src=".+" width="100%"', data)[0].split('src="')[1].split('" width="100%"')[0]
        logging.info("This article is through Wiley which uses an internal frame to display PDF files, so we are following through to %s" % (real_article_url, ))
        
        request = urllib2.Request(real_article_url)
        handle = urllib2.urlopen(request, timeout=timeout)
    
    data = handle.read()
    
    pdf_file = open(output, 'wb')
    pdf_file.write(data)
    pdf_file.close()
    
    logging.info("Article saved to %s" % (output, ))
        
    return output


def summarise_articles(articles, output, clobber=True):
    """Collects the first page from all the article filenames provided and puts
    them into a single PDF file."""
    
    if os.path.exists(output) and not clobber:
        raise IOError("Output file name exists (%s) and we've been told not to clobber it." % (output, ))
        
    output_pdf = PdfFileWriter()
    
    article_fps = []
    for article in articles:
        # Open the article
        article_fp = open(article, "rb")
        article_pdf = PdfFileReader(article_fp)
        
        # Add the first page to our summary PDF
        output_pdf.addPage(article_pdf.getPage(0))
        article_fps.append(article_fp)
        
    # Save the final PDF
    output_fp = open(output, 'wb')
    output_pdf.write(output_fp)
    output_fp.close()
    
    [article_fp.close() for article_fp in article_fps]
    
    return True


def email_article_summary(to_address, summary_filename, start_year, start_month, end_year, end_month, num_articles):
    """Emails a summary file to the given address, with brief information about
    the number of articles published by RSAA authors in the given time period."""
    
    from_address = "acasey@mso.anu.edu.au"
    host = "mso.anu.edu.au"
    body = """
            Good morning,
    
            There were %i peer-reviewed papers produced by researchers at the Research School of Astronomy & Astrophysics between %i/%i and %i/%i. A summary file containing the front page from each article is attached with this email. Please print out these summary pages, highlight the RSAA author(s) on each article and pin them to the monthly papers noticeboard.
            
            Thanks a bunch,
            
            Skynet.
            
            """ % (num_articles, start_month, start_year, end_month, end_year, )
            
    recipients = [to_address, 'acasey@mso.anu.edu.au']
    
    logging.info("Preparing summary email report for %s" % (', '.join(recipients), ))
    
    
    successful = True
    for recipient in recipients:
    
        message = MIMEMultipart()
        message["From"] = from_address
        message["To"] = recipient
        message["Subject"] = "Refereed papers summary between %i/%i and %i/%i" % (start_month, start_year, end_month, end_year, )
        message["Date"] = formatdate(localtime=True)
        
        message.attach(MIMEText(textwrap.dedent(body).lstrip()))
        
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(open(summary_filename, 'rb').read())
        Encoders.encode_base64(part)
        part.add_header('Content-Disposition', 'attachment; filename="%s"' % os.path.basename(summary_filename))
        message.attach(part)
        
        server = smtplib.SMTP(host)
        
        try:
            failed = server.sendmail(from_address, to_address, message.as_string())
            server.close()
            
        except Exception as e:
            logging.critical("Unable to send email to %s. Error: %s" % (recipient, str(e), ))
            successful = False
        
        else:
            logging.info("Email successfully sent to %s" % recipient)
    
    
    return successful
        

def report_monthly_papers(email_address, start_year, start_month, end_year, end_month, timeout):
    """Retrieves all peer-reviewed papers authored or co-authored by researchers
    at the Research School of Astronomy & Astrophysics in a given time frame, and
    emails a paperboy/girl the first page of each peer-reviewed article."""
    
    start_year = int(start_year)
    start_month = int(start_month)
    
    if end_year is None:
        end_year = start_year if 12 > start_month else start_year + 1
    else:
        end_year = int(end_year)
    
    if end_month is None:
        end_month = start_month + 1 if 12 > start_month else 1
    else:
        end_month = int(end_month)
    
    folder = '%s-%s_%s-%s' % (start_year, start_month, end_year, end_month, )
    if not os.path.exists(folder):
        os.system('mkdir %s' % (folder, ))    
    
    article_list = retrieve_article_urls(start_year, start_month, end_year=end_year, end_month=end_month, timeout=timeout)
    saved_articles = [download_article(article, '%s/%s.pdf' % (folder, bibcode, )) for bibcode, article in article_list]
    summarise_articles(saved_articles, '%s/Summary_%s.pdf' % (folder, folder, ))

    email_article_summary(email_address, '%s/Summary_%s.pdf' % (folder, folder, ), start_year, start_month, end_year, end_month, len(article_list))



if __name__ == '__main__':
    
    import argparse
    
    class LastMonthAction(argparse.Action):
        def __init__(self,
                     option_strings,
                     dest,
                     nargs=None,
                     const=None,
                     default=None,
                     type=None,
                     choices=None,
                     required=False,
                     help=None,
                     metavar=None):
            argparse.Action.__init__(self,
                                 option_strings=option_strings,
                                 dest=dest,
                                 nargs=nargs,
                                 const=const,
                                 default=default,
                                 type=type,
                                 choices=choices,
                                 required=required,
                                 help=help,
                                 metavar=metavar,
                                 )
            return
        
        def __call__(self, parser, namespace, values, option_string=None):
            
            if values == "last":
                now = datetime.now()
                month = now.month - 1
                year = now.year if now.month != 12 else now.year - 1
            
            elif values == "this":
                now = datetime.now()
                month, year = now.month, now.year
                
            
            setattr(namespace, self.dest, month)
            setattr(namespace, 'start_year', year)
            
    
    
    
    parser = argparse.ArgumentParser(prog="Paperboy", description="Retrieves recent peer-reviewed articles published by RSAA staff and emails them to a Paperboy.")
    
    #paperboy --month= --year= --to
    #month can be last, and then year is not necessary
    # end_year, end_month availabile
    
    parser.add_argument('--month', action=LastMonthAction, dest='start_month')
    parser.add_argument('--year', action='store', dest='start_year', type=int)
    
    parser.add_argument('--to', action='store', dest='to_address', type=str, default=None)
    parser.add_argument('--end_month', action='store', dest='end_month', type=int, default=None)
    parser.add_argument('--end_year', action='store', dest='end_year', type=int, default=None)
    parser.add_argument('--timeout', action='store', dest='timeout', type=int, default=120)
    parser.add_argument('--repeats', action='store', dest='repeats', type=int, default=3)
    parser.add_argument('--interval', action='store', dest='interval', type=int, default=120)
    
    results = parser.parse_args()
    
    if None not in [results.to_address, results.start_year, results.start_month]:
        
        for attempt in xrange(results.repeats):
            
            try:
                report_monthly_papers(results.to_address, results.start_year, results.start_month, results.end_year, results.end_month, results.timeout)
        
            except:
                etype, value, tb = sys.exc_info()
                logging.critical("An error occurred whilst trying to report the monthly papers:\n\tTraceback (most recent call last):\n%s\n\t%s: %s" 
                                  % ("\n".join(traceback.format_tb(tb, 5)), etype, value))
                logging.info("We will try again in %i seconds (%i attempts remaining)." % (results.interval, results.repeats - attempt - 1, ))
                time.sleep(results.interval)
                
            else:
                logging.info("Finished successfully.")
                break
            
        
            
    
