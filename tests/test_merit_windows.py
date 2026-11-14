import io
import unittest
import numpy as np
import tifffile
from research.experiments.merit_windows import RangeFile, metadata, crop


class Reply:
    def __init__(self,status,headers,data=b''):
        self.status_code,self.headers,self.data=status,headers,data
    def iter_content(self,size):
        for i in range(0,len(self.data),size): yield self.data[i:i+size]
    def close(self): pass


class Server:
    def __init__(self,data): self.data,self.calls,self.mode=data,[],None
    def head(self,*args,**kwargs):
        return Reply(200,{'ETag':'test-id','Content-Length':str(len(self.data))})
    def get(self,url,headers,**kwargs):
        self.calls.append(headers)
        a,b=map(int,headers['Range'][6:].split('-'))
        return Reply(200 if self.mode=='full' else 206,
            {'ETag':'changed' if self.mode=='changed' else 'test-id',
             'Content-Range':f'bytes {a}-{b}/{len(self.data)}'},self.data[a:b+1])


def fixture(dtype=np.uint8):
    data=np.arange(120,dtype=dtype).reshape(10,12)
    buf=io.BytesIO()
    tifffile.imwrite(buf,data,rowsperstrip=1,compression='deflate',metadata=None,
        extratags=[(33550,'d',3,(.01,.01,0),False),
                   (33922,'d',6,(0,0,0,80,30,0),False),
                   (34735,'H',12,(1,1,0,2,1025,0,1,1,2048,0,1,4326),False)])
    return data,Server(buf.getvalue())


class MeritWindowsTest(unittest.TestCase):
    def remote(self,server,maximum=100000):
        return RangeFile('https://mghydro.com/watersheds/data/flowdir45.tif',
                         {'bytes':0,'maximum_bytes':maximum},server,128)
    def test_native_crop_and_signed_values(self):
        for dtype in [np.uint8,np.int32]:
            data,server=fixture(dtype);remote=self.remote(server)
            info=metadata(remote)
            actual,t,w=crop(remote,info,[80.02,29.94,80.06,29.98],halo=0)
            c,r,width,height=w
            np.testing.assert_array_equal(actual,data[r:r+height,c:c+width])
            self.assertEqual(actual.dtype,data.dtype)
            self.assertAlmostEqual(t.c,80+c*.01)
            self.assertGreater(len(server.calls),0)
    def test_no_full_download_fallback(self):
        _,server=fixture();server.mode='full'
        with self.assertRaisesRegex(ValueError,'206'): self.remote(server).read(1)
    def test_changed_identity_rejected(self):
        _,server=fixture();server.mode='changed'
        with self.assertRaisesRegex(ValueError,'stable'): self.remote(server).read(1)
    def test_budget_preflight(self):
        _,server=fixture()
        with self.assertRaisesRegex(ValueError,'budget'): self.remote(server,64).read(1)
        self.assertEqual(len(server.calls),0)
    def test_repeated_reads_cached_and_bounded(self):
        _,server=fixture();remote=self.remote(server)
        a=remote.read(16);remote.seek(0);self.assertEqual(a,remote.read(16))
        self.assertEqual(len(server.calls),1)
        with self.assertRaises(ValueError):remote.read()
    def test_other_hosts_and_credentials_rejected(self):
        for url in ['http://mghydro.com/watersheds/data/flowdir45.tif',
                    'https://user:secret@mghydro.com/watersheds/data/flowdir45.tif',
                    'https://mghydro.com/watersheds/data/flowdir45.tif?key=1',
                    'https://example.com/watersheds/data/flowdir45.tif']:
            with self.assertRaises(ValueError): RangeFile(url,{'bytes':0,'maximum_bytes':100})
    def test_pixel_budget(self):
        _,server=fixture();remote=self.remote(server)
        with self.assertRaisesRegex(ValueError,'budget'):
            crop(remote,metadata(remote),[80,29.9,80.12,30],max_pixels=10)


if __name__=='__main__': unittest.main()
