import os
import json
import requests
#from urllib import parse
import urllib
import mcsettings as URL
import re

class Cloud():
	"""main class with mail.ru cloud APIs"""

	def __init__(self,email="",password=""):
		self.__password__ = password
		self.email = email
		self.response = None
		self.authorized = False
		self.token = ""
		self.cookies = {}
		self.loader = ""

	def __auth__(self):
		values = {"Login":self.email, "Password":self.__password__}
		self.response = requests.get(URL.AUTH, params = values)
		if self.response.status_code == requests.codes.ok:
			self.authorized = True
			self.cookies = dict(self.response.cookies)
		else:
			self.authorized = False

	def __get_token__(self):
		"""update token"""
		self.response = requests.get(URL.CLOUD, cookies = self.cookies)
		text = self.response.text
		m = re.search('"token": "(\w+)"', text)
		if m:
			self.token = m.group(0)
			return True
		else:
			return False

	def login(self):
		"""login cloud to start work """
		self.__auth__()
		self.__get_token__()

	def logout(self):
		self.response = requests.post(URL.LOGOUT,cookies = self.cookies)
		if self.response.status_code == requests.codes.ok:
			self.authorized = False
			self.cookies = {}
			self.token = ""
		else:
			self.authorized = True


	def __get_loader__(self):
		"""get the load server """
		self.response = requests.get(URL.DISPATCHER)
		self.loader = self.response.text.split(" ")[0]

	def __load_file__(self,filepath = ""):
		"""load file to cloclo, and return dict with params"""
		path = [i for i in filepath.split('/') if i]
		filename = path.pop()
		with open(filepath, 'rb') as f:
			fd = {'file': f}
			values = {"Content_Type":"multipart/form-data", "Content" : {"file":filename}}
			self.response = requests.post(self.loader, params = values, files = fd, cookies = self.cookies)

		ls = self.response.text.split(";")

		if self.response.status_code == requests.codes.ok and ls:
			return {"name":filename,
					"hash":ls[0].strip(),
					"size":ls[2].strip()
					}
		else:
			return None


	def __link_file__(self,file_params,cloud_path):
		"""Finaly add link of loaded file into cloud"""
		body = urllib.urlencode({
			"home":cloud_path + file_params["name"],
				"hash":file_params["hash"],
				"size":file_params["size"],
				"conflict":"rename",
				"api":2,
				"build":"hotfix-29-2.201502191834",
				"email": self.email,
				"x-email": self.email,
				"token": self.token,
				})
		self.response = requests.post(URL.ADDFILE, data = body, cookies = self.cookies)
		if self.response.status_code == requests.codes.ok:
			return True
		else:
			return False

	def add_folder(self,full_folder_name = ""):
		"""Generate full path to file every time, even if exist """
		ls  = full_folder_name.split('/')
		cls = [item for item in ls if item]
		parpath = ""
		for foldername, parent in self.__gen_parents__(cls):
			parpath+="/"+parent
			body = urllib.urlencode({
					"add": json.dumps([{
							"folder":parpath,
							"name": foldername,
					}]),
					"api":2,
					"email": self.email,
					"storage":"home",
					"token": self.token,
			})
			self.response = requests.post(URL.ADDFOLDER,data = body, cookies = self.cookies)

		if self.response.status_code == requests.codes.ok:
			return True
		else:
			return False

	def __gen_parents__(self, ls):
		f=[]
		par = "/"
		for i in ls:
			if par == "/":
				f.append((i,par))
				par = i
			else:
				f.append((i,par))
				par = i
		return f

	def add_file(self,local_path,cloud_path):
		"""Load file into cloud 
		-- local_path = path on the local machine
		-- cloud_path = path you want to load in cloud , if not exists will be created
		 """
		self.__get_loader__()
		params = self.__load_file__(local_path)
		self.__link_file__(params,cloud_path)

	def share(self,filename_with_path=""):
		"""share the file from cloud """
		body = urllib.urlencode({
					"ids": json.dumps([filename_with_path]),
					"api":2,
					"email": self.email,
					"storage":"home",
					"token": self.token,
			})
		self.response = requests.post(URL.SHARE,data = body, cookies = self.cookies)
		if self.response.status_code == requests.codes.ok:
			return self.response.json()["body"][0]["url"]["get"]
		else:
			return None

	def load_folder(self,local_path,cloud_path):
		"""Load folder into cloud recursively"""
		abs_path = os.path.abspath(local_path)
		local_path_length = len(abs_path) + 1

		self.add_folder(cloud_path)

		for root, dirs, files in os.walk(abs_path):
			local_current_dir = root[local_path_length:]
			cloud_current_dir = cloud_path + '/' + local_current_dir
			self.add_folder(cloud_current_dir)
			for file in files:
				self.add_file(root + '/' + file, cloud_current_dir)

	def unshare(self, filename_with_path=""):
		"""unshare the file """
		body = urllib.urlencode({
					"ids": json.dumps([filename_with_path]),
					"api":2,
					"email": self.email,
					"storage":"home",
					"token": self.token,
			})
		self.response = requests.post(URL.UNSHARE,data = body, cookies = self.cookies)
		if self.response.status_code == requests.codes.ok:
			return True
		else:
			return False

	def remove(self, full_path=""):
		"""Remove files, folders all of them, use CAREFULL """
		body = urllib.urlencode({
					"ids": json.dumps([full_path]),
					"api":2,
					"email": self.email,
					"storage":"home",
					"token": self.token,
			})
		self.response = requests.post(URL.REMOVE,data = body, cookies = self.cookies)
		if self.response.status_code == requests.codes.ok:
			return True
		else:
			return False

	def move(self, current_path="", target_path=""):
		"""Move file or folder in cloud """
		body = urllib.urlencode({
					"folder": target_path,
					"ids": json.dumps([current_path]),
					"api":2,
					"email": self.email,
					"storage":"home",
					"token": self.token,
			})
		self.response = requests.post(URL.MOVE,data = body, cookies = self.cookies)
		if self.response.status_code == requests.codes.ok:
			return True
		else:
			return False


	def rename(self, current_name="", target_name=""):
		"""Rename file or folder in cloud 
		-- current_name = full path + name 
		-- target_name = only name of file
		"""
		body = urllib.urlencode({
					"rename": json.dumps([{
						"id": current_name,
						"name":target_name,
						}]),
					"api":2,
					"email": self.email,
					"storage":"home",
					"token": self.token,
			})
		self.response = requests.post(URL.RENAME,data = body, cookies = self.cookies)
		if self.response.status_code == requests.codes.ok:
			return True
		else:
			return False


