from odoo import api, fields, models, _
import base64,hashlib,time,os,traceback,logging,re
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class SplitInvoice(models.TransientModel):
    _name = "tt.upload.center.wizard"
    _description = 'Upload Center Wizard'

    filename = fields.Char('Filename',required=True, default='filename')
    file_description = fields.Text('File Description',required=True)
    file = fields.Binary('File',required=True)


    def upload(self):
        pattern = re.compile('^[a-zA-Z0-9](?:[a-zA-Z0-9 ._-]*[a-zA-Z0-9])?\.[a-zA-Z0-9_-]+$')
        if not pattern.match(self.filename):
            raise UserError('Filename Is Not Valid')
        try:
            print("upload")
            path,url = self.create_directory_structure(self.filename)
            # path = '/home/rodex-it-05/Documents/test/upload_odoo/%s' % (self.filename)
            file = open(path,'wb')
            file.write(base64.b64decode(self.file))
            file.close()

            self.env['tt.upload.center'].sudo().create({
                'filename': self.filename,
                'file_description': self.file_description,
                'path': path,
                'url': url
            })
        except Exception as e:
            _logger.error(traceback.format_exc())

    def create_directory_structure(self,filename):
        base_dir = '/src/static/'
        base_url = 'https://static.rodextrip.com/'
        valid_path = False

        while (not valid_path):
            hash = hashlib.md5(('%s%s' % (filename,time.time())).encode()).hexdigest()
            depth = 3
            length = 3
            hash_only_path = self.make_list_dir(hash,depth,length)
            hashed_path = '%s%s/' % (base_dir,hash_only_path)
            full_path = '%s%s' % (hashed_path,filename)


            if not os.path.exists(full_path):
                if not os.path.exists(hashed_path):
                    os.makedirs(hashed_path)
                valid_path = True

        return full_path,'%s%s/%s' % (base_url,hash_only_path,filename)


    def make_list_dir(self,hash,depth,length):
        result = []
        for n  in range (1,depth+1):
            curr_n = -n*length
            if n>1:
                result.append(hash[curr_n:curr_n+length])
            else:
                result.append(hash[curr_n:])
        return '/'.join(result)