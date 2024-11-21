# vim: ts=4 sw=4 noexpandtab
import os

def DirectoryOfThisScript():
	return os.path.dirname(os.path.realpath(__file__)) + os.sep
#enddef

def WafFolder():
	return os.path.join(DirectoryOfThisScript(), 'waf')
#enddef

def Settings(**kwargs):
	return {
		'sys_path': [ WafFolder() ] # Python
	}
#enddef
