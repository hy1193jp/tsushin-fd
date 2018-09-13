# -*- coding: utf-8 -*-

from flask import Flask, flash, render_template, request, redirect, Response, url_for #, send_file
from google.appengine.ext import ndb
from google.appengine.api import app_identity, mail
import cloudstorage as gcs
import datetime
import os, logging
# ex. logging.info(p.kamoku)

bucket_name = 'tsushin-fd.appspot.com'

app = Flask(__name__)

class Paper(ndb.Model):
    kamoku = ndb.StringProperty()
    ufilename = ndb.StringProperty()
    udate = ndb.DateTimeProperty(auto_now=True)

@app.route('/', methods = ['GET', 'POST'])
def main():
    if request.method == 'POST':
        if request.form['cd']:
            k = ndb.Key(Paper, request.form['cd'])
            ep = k.get()	#enquete paper
        else:
            ep = None
        if not ep:
            return render_template('main.html',cd=request.form['cd'],
                                 error=u'正しい整理番号を指定してください')
        uf = request.files['file']	# upload file
        if uf.filename == '':
          return render_template('main.html',
                                 error=u'ファイルを指定してください')
        # The retry_params specified in the open call will override the default
        # retry params for this particular file handle.
        write_retry_params = gcs.RetryParams(backoff_factor=1.1)
        f = request.form['cd'] + '_' +  \
                datetime.datetime.now().strftime('%Y%m%d') + os.path.splitext(uf.filename)[1]
        gcs_file = gcs.open('/' + bucket_name + '/uploaded/' + f,
                      'w', content_type = 'application/msexcel',
                       retry_params = write_retry_params)
        gcs_file.write(uf.read())
        gcs_file.close()
        ep.ufilename = uf.filename
        ep.put()
        mail.send_mail(sender = 'ymd@mbd.ocn.ne.jp',
                   to = "admin <hiroaki.yamada@itp.kindai.ac.jp>",
                   subject = "tsushin-fd uploaded",
                   body = 'uploaded {:s} at {:s}'.format(ep.kamoku.encode('utf-8'), f))
        #return redirect(url_for('submitted_form'))
        return render_template('main.html',
            msg = request.form['cd'] + ep.kamoku + '---' + uf.filename + u'はアップロードされました')
    return render_template('main.html')


@app.errorhandler(404)
def page_not_found(e):
    """Return a custom 404 error."""
    return 'Sorry, nothing at this URL.', 404

@app.route('/mng', methods=['GET', 'POST'])
def mng():
    if request.method == 'POST':
        file = request.files['file']
        if file and request.form['pw'] == 'import':
            import csv
            for l in csv.reader(file):
              Paper(id=l[0], kamoku=l[1]).put()
            return (str(Paper.query().count()))
        elif request.form['pw'] == 'export':
            (f, c) = exportCSV()
            return '{1:d} records write to {0:s}'.format(f, c)
    return '''
    <!doctype html>
    <title>mng</title>
    <form action="" method=post enctype=multipart/form-data>
      <p>enquete info.<input type=file name=file>
         <input type="password" size=8 name=pw>
         <input type=submit value=Submit></p>
    </form>
    '''

def exportCSV():
    write_retry_params = gcs.RetryParams(backoff_factor=1.1)
    f = 'Paper{:%Y%m%d}.csv'.format(datetime.datetime.now())
    gcs_file = gcs.open(bucket_name + '/wk/' + f,
            'w', content_type='text/csv',
            retry_params=write_retry_params)
    c = 0
    for p in Paper.query():
        if p.ufilename:
            l = (p.key.id(), p.kamoku, p.ufilename, p.udate.isoformat())
        else:
            l = (p.key.id(), p.kamoku, '', '')           
        gcs_file.write(','.join(l).encode('cp932') + '\r\n') 
        c += 1
    gcs_file.close()
    return (f, c)
#    return send_file('main.py')

#  bucket_name = os.environ.get('BUCKET_NAME',
#                             app_identity.get_default_gcs_bucket_name())
#  return 'Using bucket name: ' + bucket_name + '\n\n'

#@app.route('/submitted')
#def submitted_form():
#    return render_template('submitted_form.html', name='cd')

app.secret_key = os.urandom(24)
app.jinja_env.globals['nowts'] = datetime.datetime.now()
