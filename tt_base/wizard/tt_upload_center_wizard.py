import pytz
from datetime import datetime, timedelta

from odoo import api, fields, models, _
import base64,hashlib,time,os,traceback,logging,re
from odoo.exceptions import UserError
from ...tools import ERR
import odoo.tools as tools
from PIL import Image

_logger = logging.getLogger(__name__)

class SplitInvoice(models.TransientModel):
    _name = "tt.upload.center.wizard"
    _description = 'Upload Center Wizard'

    filename = fields.Char('Filename',required=True, default='filename')
    file_reference = fields.Text('File Description',required=True)
    delete_time = fields.Datetime('Deleted Time')
    file = fields.Binary('File',required=True)
    target_field_name = fields.Char("Target Field")
    ho_id = fields.Many2one('tt.agent', 'Head Office ID', domain=[('is_ho_agent', '=', True)], default=lambda self: self.env.user.ho_id)
    agent_id = fields.Many2one('tt.agent','Agent ID')
    owner_id = fields.Many2one('res.users','Owner ID')

    def upload_from_button(self):
        # self.upload(self.filename,self.file_reference,base64.b64decode(self.file))
        if self.agent_id:
            co_agent_id = self.agent_id.id
        else:
            co_agent_id = self.env.user.agent_id.id
        if self.owner_id:
            co_uid = self.owner_id.id
        else:
            co_uid = self.env.user.id

        context = {
            'co_agent_id': co_agent_id,
            'co_uid': co_uid
        }
        upload_res = self.upload(self.filename,self.file_reference,self.file,context,self.delete_time)
        if self.target_field_name:
            if upload_res['error_code'] == 0:
                upload_res = upload_res['response']
                active_id = self.env.context['active_id']
                active_model = self.env.context['active_model']
                offline_record = self.env[active_model].browse(active_id)
                upload_obj = self.env['tt.upload.center'].search([('seq_id','=',upload_res['seq_id'])],limit=1)
                if offline_record._fields[self.target_field_name].type == 'many2one':
                    write_vals = {
                        self.target_field_name: upload_obj.id
                    }
                else:
                    write_vals = {
                        self.target_field_name: [(4, upload_obj.id)]
                    }
                # supaya jika issued offline attachmentny terhapus stlh 3 bulan
                if active_model == 'tt.reservation.offline':
                    upload_obj.will_be_deleted_time = datetime.now() + timedelta(days=90)
                offline_record.write(write_vals)


    def upload_file_api(self,data,context):
        return self.upload(data['filename'],data['file_reference'],data['file'],context,data.get('delete_date'))

    #file is encoded in base64
    def upload(self,filename,file_reference,file,context,delete_time=False):
        # old regex checker, deprecated
        # pattern = re.compile('^[a-zA-Z0-9](?:[a-zA-Z0-9 ()._-]*[a-zA-Z0-9)])?\.[a-zA-Z0-9_-]+$')
        # if not pattern.match(filename):
        #     raise UserError('Filename Is Not Valid')

        ##prevent uploading malicious files extension
        pattern = re.compile('\\bjpg\\b$|\\bjpeg\\b$|\\bpng\\b$|\\bpdf\\b$|\\bwebp\\b$|\\bhtml\\b$|\\bxls\\b$|\\bxlsx\\b$|\\bdoc\\b$|\\bdocx\\b$|\\bcsv\\b$|\\bgif\\b$', re.IGNORECASE)
        if not pattern.search(filename):
            raise UserError('Something went wrong, please contact admin.')

        prohibited_pattern = r'[\\/:*?"<>|]'
        filename = re.sub(prohibited_pattern,'_',filename)
        try:
            path,url = self.create_directory_structure(filename)
            # path = '/home/rodex-it-05/Documents/test/upload_odoo/%s' % (self.filename)
            new_file = open(path,'wb')
            new_file.write(base64.b64decode(file))
            new_file.close()

            #compressing image
            try:
                file_type = filename.split('.')[1]
                if file_type in ['jpg','jpeg','png','svg']:
                    raw_image = Image.open(path)
                    raw_image.save(path,optimize=True,quality=30)
            except:
                _logger.error(traceback.format_exc())

            ho_agent_obj = False
            agent_obj = self.env['tt.agent'].browse(context['co_agent_id'])
            if agent_obj:
                ho_agent_obj = agent_obj.ho_id

            new_uploaded_data = self.env['tt.upload.center'].sudo().create({
                'filename': filename,
                'file_reference': file_reference,
                'path': path,
                'url': url,
                'agent_id': context['co_agent_id'],
                'upload_uid': context['co_uid'],
                'will_be_deleted_time': delete_time,
                'ho_id': ho_agent_obj and ho_agent_obj.id or False
            })

            _logger.info('Finish Upload')
            return ERR.get_no_error({
                'filename' : new_uploaded_data.filename,
                'file_reference': new_uploaded_data.file_reference,
                'url': new_uploaded_data.url,
                'seq_id': new_uploaded_data.seq_id
            })
        except Exception as e:
            _logger.error('Exception Upload Center')
            _logger.error(traceback.format_exc())
            return ERR.get_error()

    def create_directory_structure(self,filename):
        base_dir = '/src/static/'
        base_url = tools.config.get('static_url','')
        valid_path = False

        while (not valid_path):
            hash = hashlib.md5(('%s%s' % (filename,time.time())).encode()).hexdigest()
            depth = 3
            length = 4
            hash_only_path = '%s/%s/' % (datetime.now(pytz.timezone('Asia/Jakarta')).strftime('%Y/%m/%d'),self.make_list_dir(hash,depth,length))
            hashed_path = '%s%s' % (base_dir,hash_only_path)
            full_path = '%s%s' % (hashed_path,filename)


            if not os.path.exists(full_path):
                if not os.path.exists(hashed_path):
                    os.makedirs(hashed_path)
                valid_path = True

        return full_path,'%s/%s%s' % (base_url,hash_only_path,filename)

    def make_list_dir(self,hash,depth,length):
        result = []
        for n in range (1,depth+1):
            curr_n = -n*length
            if n>1:
                result.append(hash[curr_n:curr_n+length])
            else:
                result.append(hash[curr_n:])
        return '/'.join(result)
