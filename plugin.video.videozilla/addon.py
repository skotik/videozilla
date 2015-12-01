# encoding: utf-8
from xbmcswift2 import Plugin, CLI_MODE, xbmcgui
from datetime import timedelta
import re, urllib2, urllib, json, cookielib, time

urlroot='http://videozilla.ru'

plugin = Plugin()

if CLI_MODE:
	import codecs, sys
	outf = codecs.getwriter('cp866')(sys.stdout, errors='replace')
	sys.stdout = outf


STRINGS = {
    'search': 33005,
	'prev'  : 33001,
	'next'  : 33002,
	'prompt'  : 33003,
	'pubdate'  : 33010,
	'rating'  : 33011,
	'hits'  : 33012,
	'all'  : 33013,
	'month'  : 33014,
	'week'  : 33015,
	'today'  : 33016,
	'unmodered'  : 33017,
}

ORDERBY = ['pubdate','rating','hits']
PERIOD = ['all','month','week','today']

BadType='exe pdf 7z rar mp3 iso other ac3 wav doc txt'


@plugin.cached(TTL=5)
def GetPage(request):
	request=json.loads(request)
	links = []
	cj = cookielib.CookieJar()
	opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
#	opener = urllib2.build_opener()
	opener.addheaders = [('X-Requested-With', 'XMLHttpRequest')]
	#if 'catI'
	data = { 'of_ajax' : '1',
		'orderby': request['orderby'],
		'cat_id' : request['cat_id'] if 'cat_id' in request else '31',
		'page'   : request['page'],
		'period' : request['period'],
	}
	page = int(request['page'])
	if request['query'] is not None and request['query']!='':
		data['title']=request['query']
		data['cat_id']=''
		s_url='http://videozilla.ru/video/search?'+urllib.urlencode(data)
#		print s_url
		resp=opener.open(s_url, None, 30)
	else:
		request['query']=''
		s_url='http://videozilla.ru/video'
		resp=opener.open(s_url, urllib.urlencode(data), 30)
#		print repr(data)

	s_resp=resp.read()
	s_resp=s_resp.decode('utf_8','replace')
	s_resp=re.sub(ur'^.*?<!-- Вывод модуля maintop -->','',s_resp,re.S);
	s_resp=re.sub(ur'<!-- Вывод модуля mainbottom -->.*?$','',s_resp,re.S);
	links = ParsePage(s_resp)

	m_next=re.search(ur'class="pagebar_page">Следующая</a>',s_resp,re.S)
	if m_next is not None:
		links.append({
			'label': _('next'),
			'path': plugin.url_for('index' if request['query']=='' else 'search', page=str(page + 1), orderby=request['orderby'], period=request['period'], query=request['query'])
		})


	if page > 1:
		links.insert(0, {
			'label': _('prev'),
			'path': plugin.url_for('index' if request['query']=='' else 'search', page=str(page - 1), orderby=request['orderby'], period=request['period'], query=request['query'])
		})

	return links


def ParsePage(content):
	s_resp = content
	links = []
	mPubs=re.findall(ur'(?:<li class="preview(?:"| media")>(.*?)</ul>)', s_resp, re.DOTALL)
	fThumInTree=plugin.get_setting('ThumInTree', bool)
	fNotChild=plugin.get_setting('NotChild', bool)
	for cPub in mPubs:
#		print cPub.decode('utf8').encode('cp866')
		info={}
		info_thum=None
		cPubHTML=cPub
		label_format=''
		vurl=''
		lDuration=None
		m_url=re.search(ur'<a title=".*?" href="(.*?)" class="thumb"[^>]*>',cPubHTML,re.S)
		if m_url is not None:
			vurl=m_url.group(1)
#		m_title=re.search(ur'<span class="thumb-title">(.*?)</span>',cPubHTML,re.S)
		m_title=re.search(ur'<h5><a.*?>(.*?)</a></h5>',cPubHTML,re.S)
		if m_title is not None:
			info['title']=m_title.group(1)
#		else:
#			print cPub.decode('utf_8','ignore')
		if fThumInTree:
			m_thum=re.search('<img src="(.*?)"  alt=".*?" />',cPubHTML,re.S)
			if m_thum is not None:
				info_thum=urlroot+m_thum.group(1)

		m_genre=re.search(ur'<div class="icn-cat">.*?<a href="(.*?)" title="(.*?)">[^<]*</a>',cPubHTML,re.S)
		if m_genre is not None:
			info['genre']=m_genre.group(2)
		else:
			m_genre=re.search(ur'<span class="glyphicon glyphicon-facetime-video"></span> <a href="(.*?)" title=".*?">(.*?)</a>',cPubHTML,re.S)
			if m_genre is not None:
				info['genre']=m_genre.group(2)
		m_votes=re.search(ur'<span class="glyphicon glyphicon-star"></span> (\d+)',cPubHTML,re.S)
		if m_votes is not None:
			info['votes']=m_votes.group(1)
			m_rate=re.search(ur'<span class="glyphicon glyphicon-eye-open"></span> (\d+)',cPubHTML,re.S)
			if m_rate is not None:
				l_rate=float(info['votes'])
				l_rate=l_rate*l_rate/100.0*10.0
				l_rate=l_rate if l_rate<=10 else 10.0
#				print l_rate
				info['rating']=l_rate
	
		m_duration=re.search(ur'<span title="Длительность" class="duration">(.*?)</span>',cPubHTML,re.S)
		if m_duration is not None:
			lDuration=time.strptime(m_duration.group(1),'%H:%M:%S')
			lDuration=timedelta(hours=lDuration.tm_hour, minutes=lDuration.tm_min, seconds=lDuration.tm_sec)
			lDuration=lDuration.seconds + lDuration.days * 24 * 3600
#			print lDuration
#			info['duration']=m_duration.group(1)

		
		m_cens=re.search(ur'<span class="censored">',cPubHTML,re.S)
		if m_cens is not None:
			info['mpaa']='18+'
			if not fNotChild:
				continue

#		print repr(info)
#		if fIconInTree:
#			info_icon='http://matrixportal.ru/covers/'+m_link.group(1)+'_3.jpg'
#		print repr(vurl)
		links.append({
#				'icon'      : info_icon,
				'thumbnail' : info_thum,
				'label'     : info['title'], 
				'path'      : plugin.url_for('playvideo', url=vurl),
				'info': info,
				'stream_info': {
					'video': {'duration': lDuration},
				},
				'is_playable': True
			})		

	return links

def multiparse(outreg,inreg,text):
	result = []
	m_out=re.search(outreg,text,re.S)
	if m_out is not None:
		m_in=re.findall(inreg,m_out.group(1),re.S)
		for sFind in m_in:
			result.append(sFind)
	return result




#@plugin.route('/playvideo/<url>')
@plugin.cached_route('/playvideo/<url>',TTL=5)
def playvideo(url):
	s_url=urlroot+url
	cj = cookielib.CookieJar()
	opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
	opener.addheaders = [('X-Requested-With', 'XMLHttpRequest')]
	resp=opener.open(s_url, None, 30)
	s_resp=resp.read()
	s_resp=s_resp.decode('utf_8','replace')
	m_cens=re.search('<form class="accept_form".*?>.*?name="csrf_token" value="(.*?)".*?name="accept" value="(.*?)".*?</form>',s_resp,re.S)
#	print 'step 1'
	if m_cens is not None:
		fNotChild=plugin.get_setting('NotChild', bool)
		if fNotChild:
			data = { 'csrf_token':m_cens.group(1), 'accept':m_cens.group(2) }
			resp=opener.open(s_url, urllib.urlencode(data), 30)
			s_resp=resp.read()
			s_resp=s_resp.decode('utf_8','replace')
#			print repr(data)


	m=re.search("var movie_id = '(\d+)';",s_resp, re.S)
	streamurl=None
	if m is not None:
		resp=opener.open('http://videozilla.ru/components/video/ajax/get_movie_code.php?id='+m.group(1), None, 30)
		s_resp=resp.read()
		s_resp=s_resp.decode('utf_8','replace')
		m_json=re.search('"sources":(\[.*?\])',s_resp, re.S)
		if m_json is not None:
			for source in json.loads(m_json.group(1)):
				if streamurl is None:
					streamurl=source['file']
				if source['default']:
					streamurl=source['file']

	if CLI_MODE:
		print streamurl
		return []
	else:
		plugin.set_resolved_url(streamurl)


@plugin.route('/clearcache')
def clearcache():
	plugin.clear_function_cache();


@plugin.route('/', name='ShowMain', options={'period':None})
@plugin.route('/unmodered', name='ShowUnModered', options={'period':'_unmodered'})
@plugin.route('/select/<period>')
def root(period):
	items = []
	if period=='_unmodered':
		request = json.dumps({'orderby':'pubdate','period':'all','page':'1','query':None,'cat_id':'39'})
		return list(GetPage(request))
		
	if period is None:
		for c_period in PERIOD:
			items.append({'label':_(c_period), 
				'path': plugin.url_for('root', period=c_period) })
		items.insert(0, {
			'label': _('unmodered'),
			'path': plugin.url_for('ShowUnModered')
		})
		items.insert(0, {
			'label': _('search'),
			'path': plugin.url_for('SearchAll')
		})
	else:
		for c_orderby in ORDERBY:
			items.append({'label':_(c_orderby), 
				'path': plugin.url_for('index', period=period, orderby=c_orderby, page='1') })
		items.insert(0, {
			'label': _('search'),
			'path': plugin.url_for('SearchPeriod',period=period)
		})
	return items



@plugin.route('/vcat', name='ShowAll', options={'orderby': 'pubdate', 'period':'all', 'page':'1'})
@plugin.route('/vcat/<period>', name='ShowPeriod', options={'orderby':'pubdate', 'page':'1'})
@plugin.route('/vcat/<period>/<orderby>', name='ShowOrderby', options={'page':'1'})
@plugin.route('/vcat/<period>/<orderby>/<page>')
def index(period,orderby,page):
	items = []
	request = json.dumps({'orderby':orderby,'period':period,'page':page,'query':None})
	items = list(GetPage(request))

	if page=='1':
		items.insert(0, {
			'label': _('search'),
			'path': plugin.url_for('SearchOrderStart',period=period,orderby=orderby)
		})

	return plugin.finish(items, update_listing=True, sort_methods=['playlist_order', 'video_rating'])
	pass

@plugin.route('/video/<id>')
def show_videos(id):
	items = list(ParseVideo(id))
#	return plugin.finish(items)
	return items
	pass

@plugin.route('/search', name='SearchAll', options={'orderby': 'pubdate', 'period':'all', 'page':'1', 'query':None})
@plugin.route('/search/<period>', name='SearchPeriod', options={'orderby':'pubdate', 'page':'1', 'query':None})
@plugin.route('/search/<period>/<orderby>/', name='SearchOrderStart', options={'page':'1','query':None})
@plugin.route('/search/<period>/<orderby>/<page>', name='SearchOrder', options={'query':None})
@plugin.route('/search/<period>/<orderby>/<page>/<query>')
def search(period,orderby,page,query):
	request = {'orderby':orderby,'period':period,'page':page,'query':query}
	items = []
	if query is None or query=='':
		query = plugin.keyboard(heading=_('prompt'))
		if query is not None and len(query)>1:
			if CLI_MODE: 
				query=query.decode('cp866','replace').encode('utf_8')
			else:
				query=query.decode('utf_8').encode('utf_8')
		else:
			return None
		page = '1'
#	else:
#		print 'repr '+repr(query)
#		query=query.encode('latin')
	request['query']=query
	request=json.dumps(request)
	items = list(GetPage(request))

	return plugin.finish(items, update_listing=True)


def _(string_id):
    if string_id in STRINGS:
        return plugin.get_string(STRINGS[string_id]).encode('utf-8')
    else:
        log('String is missing: %s' % string_id)
        return string_id

def translit(name):
	slovar = {
	  u'а':'a' ,u'б':'b' ,u'в':'v' ,u'г':'g'  ,u'д':'d',u'е':'e',u'ё':'e',
      u'ж':'zh',u'з':'z' ,u'и':'i' ,u'й':'i'  ,u'к':'k',u'л':'l',u'м':'m',u'н':'n',
      u'о':'o' ,u'п':'p' ,u'р':'r' ,u'с':'s'  ,u'т':'t',u'у':'u',u'ф':'f',u'х':'h',
      u'ц':'c' ,u'ч':'cz',u'ш':'sh',u'щ':'scz',u'ъ':'' ,u'ы':'y',u'ь':'' ,u'э':'e',
      u'ю':'u' ,u'я':'ja',u'А':'a' ,u'Б':'b'  ,u'В':'v',u'Г':'g',u'Д':'d',u'Е':'e', u'Ё':'e',
      u'Ж':'zh',u'З':'z' ,u'И':'i' ,u'Й':'i'  ,u'К':'k',u'Л':'l',u'М':'m',u'Н':'n',
      u'О':'o' ,u'П':'p' ,u'Р':'r' ,u'С':'s'  ,u'Т':'t',u'У':'u',u'Ф':'f',u'х':'h',
      u'Ц':'c' ,u'Ч':'cz',u'Ш':'sh',u'Щ':'scz',u'Ъ':'' ,u'Ы':'y',u'Ь':'' ,u'Э':'e',
      u'Ю':'u' ,u'Я':'ja',u',':''  ,u'?':''   ,u' ':'_',u'~':'' ,u'!':'' ,u'@':''   ,u'#':'',
      u'$':''  ,u'%':''  ,u'^':''  ,u'&':''   ,u'*':'' ,u'(':'' ,u')':'' ,u'-':''   ,u'=':'', u'+':'',
      u':':''  ,u';':''  ,u'<':''  ,u'>':''   ,u'\'':'',u'"':'' ,u'\\':' ',u'/':''  ,u'№':'',
      u'[':''  ,u']':''  ,u'{':''  ,u'}':''}
#	print repr(name)
	for key in slovar:
		name = name.replace(key, slovar[key])
	return name




if __name__ == '__main__':
    plugin.run()

