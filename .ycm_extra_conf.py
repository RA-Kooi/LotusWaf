# vim: ts=4 sw=4 noexpandtab
import os

def WafFolder():
	cwd = os.curdir
	for node in os.listdir(cwd):
		wafdir = os.path.join(cwd, node)
		isDir = os.path.isdir(wafdir)
		if isDir and 'waf3-' in node:
			return wafdir
		#endif
	#endfor
#enddef

def Settings(**kwargs):
	return {
		'sys_path': [ WafFolder() ] # Python
	}
#enddef
