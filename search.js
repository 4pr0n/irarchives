/* Everything related to searching, displaying, fancy UI tweaks, etc.
   I Should probably split this into separate JS files... */

// Shortened version of getElementById
function gebi(id) { return document.getElementById(id); }

// Statusbar (overwrites previous text)
function statusbar(text) { gebi("status").innerHTML = text; }

// Output (appends text)
function output(text)          { gebi("output").innerHTML          += text + "<br>"; }
function output_posts(text)    { gebi("output_posts").innerHTML    = text; }
function output_comments(text) { gebi("output_comments").innerHTML = text; }
function output_related(text)  { gebi("output_related").innerHTML  = text; }

// Redirect to the page so the URL changes & we know what image is being searched
function redirect_search() {
	var url = gebi("url").value;
	url = url.replace(/[.]/g, '%2E');
	url = encodeURIComponent(url);
	document.location.href = document.location.pathname + '?url=' + url;
}

function search_click() {
	var url = gebi("url").value;
	// Handle modifiers
	if (url.indexOf('text:') == 0) {
		sendSearchRequest('search2.cgi?text=' + url.substr(5));
	} else if (url.indexOf('cache:') == 0) {
		sendSearchRequest('search2.cgi?cache=' + url.substr(6));
	} else if (url.indexOf('user:') == 0) {
		sendSearchRequest('search2.cgi?user=' + url.substr(5));
	} else if (url.indexOf('.') == -1) {
		// No period, assume username
		sendSearchRequest('search2.cgi?user=' + url);
	} else {
		// Assume URL search
		if (url.indexOf('://') == -1) {
			url = 'http://' + url;
		}
		sendSearchRequest('search2.cgi?url=' + url);
		gebi('url').blur();
	}
}

function redirect_user() {
	var user = gebi("user").value;
	document.location.href = document.location.pathname + '?user=' + user;
}

function user_click() {
	var user = gebi("user");
	sendSearchRequest('search2.cgi?user=' + user.value);
	user.blur();
}

function searchKeyDown(evt) {
	var theEvent = evt || window.event;
	var key = theEvent.keyCode || theEvent.which;
	key = String.fromCharCode( key );
	if (theEvent.keyCode == 13) {
		redirect_search(); // search_click();
	}
}

function userKeyDown(evt) {
	var theEvent = evt || window.event;
	var key = theEvent.keyCode || theEvent.which;
	key = String.fromCharCode( key );
	if (theEvent.keyCode == 13) {
		redirect_user(); //user_click();
	}
}

function getExternalSearchLinks(url) {
	var out = '';
	out += '<div style="text-align: left;">';
	out += '<ul>';
	out += '<li> <a class="external_link" ';
	out +=         'href="data:text/html;charset=utf-8, ';
	out +=                '<html><head><meta http-equiv=\'REFRESH\' content=\'0;url=';
	out +=         	      'http://images.google.com/searchbyimage?image_url=' + url + '\'></head></html>" ';
	out +=         'rel="noreferrer">search on google images</a></li>';
	out += '<li> <a class="external_link" ';
	out +=         'href="data:text/html;charset=utf-8, ';
	out +=                '<html><head><meta http-equiv=\'REFRESH\' content=\'0;url=';
	out +=                'http://www.tineye.com/search?pluginver=bookmark_1.0&url=' + url + '\'></head></html>" ';
	out +=         'rel="noreferrer">search on tineye</a></li>';
	out += '<li> <a class="external_link" ';
	out +=         'href="data:text/html;charset=utf-8, ';
	out +=                '<html><head><meta http-equiv=\'REFRESH\' content=\'0;url=';
	out +=                'http://www.karmadecay.com/' + url.replace(/http:\/\//, '') + '\'></head></html>" ';
	out +=         'rel="noreferrer">search on karmadecay</a></li>';
	out += '</ul>';
	out += '</div>';
	return out;
}

// Sends asynchronous XML request, handles response
function sendSearchRequest(query) {
	var request = makeHttpObject();
	statusbar('<img src="images/spinner_dark.gif"/> searching...');
	setTimeout( function() {
		var status = gebi("status");
		if (status.innerHTML.indexOf('searching...') >= 0) {
			status.innerHTML += '<br>the site is currently lagging. you can keep waiting or try again later.';
			var url = gebi('url').value.replace(/</g, '').replace(/>/g, '');
			var out = getExternalSearchLinks(url);
			status.innerHTML += out;
		}  
	}, 5000);
	gebi("output").innerHTML = '';
	output_posts('');
	output_comments('');
	request.open("GET", query, true);
	request.send(null);
	request.onreadystatechange = function() {
		if (request.readyState == 4) { 
			if (request.status == 200) {
				// success
				handleSearchResponse(request.responseText);
			} else {
				// error
				statusbar('<span class="search_count_empty">error: status ' + request.status + '</span>');
			}
		}
	}
}

function handleSearchResponse(responseText) {
	if (responseText == null || responseText == '') {
		statusbar('<span class="search_count_empty">invalid URL</span>')
		return;
	}
	var resp = JSON.parse(responseText);
	if (resp['error'] != null) {
		statusbar('<span class="search_count_empty">error: ' + resp['error'] + '</span>');
		return;
	}
	if (resp['err'] != null) {
		statusbar('<span class="search_count_empty">' + resp['err'] + '</span>');
		return;
	}
	if (resp['url'] != null) {
		gebi('url').value = resp['url']
	}
	if (resp['images'] != null) {
		// Image results for album
		var out = '<center><table>';
		out += '<tr><td colspan="5" class="search_result_title">' + resp.images.length + ' album images</td></tr>';
		out += '<tr>';
		for (var i = 0; i < resp.images.length; i++) {
			var url = resp.images[i].url;
			var thumb = '';
			if (true || resp.images[i].thumb == null) {
				var tempi = url.lastIndexOf('.');
				thumb = url.substr(0, tempi) + 's' + url.substr(tempi);
			} else {
				thumb = resp.images[i].thumb;
			}
			out += '<td align="center" valign="center" style="text-align: center; vertical-align: center;">';
			out += '<a href="' + url + '">';
			out += '<img src="' + thumb + '">';
			out += '</a>';
			//out += resp.images[i];
			out += '</td>';
			if (i % 5 == 4) {
				out += '</tr><tr>';
			}
		}
		out += '</td></tr>';
		out += '</table>';
		out += '<div class="search_result_title">' + resp.images.length + ' album links</div>';
		out += '<div style="padding: 20px; font-size: 0.8em;">';
		for (var i = 0; i < resp.images.length; i++) {
			out += '<a href="' + resp.images[i].url + '">';
			out += resp.images[i].url;
			out += '</a><br>';
		}
		out += '</center>';
		output(out);
		statusbar('');
		return;
	}
	if (resp.posts.length == 0 && resp.comments.length == 0) {
		// No results, show alternatives
		statusbar('<span class="search_count_empty">no results</span>');
		
		var url = gebi('url').value.replace(/</g, '').replace(/>/g, '');
		if (document.location.href.indexOf('?user=') == -1) {
			var out = getExternalSearchLinks(url);
			output(out);
		} else {
			output('<br>');
		}
		return;
	}
	statusbar('');
	
	// POSTS
	if (resp.posts.length > 0) {
		var result = [];
		result.push('<table border="1" style="border-style: solid; padding: 5px; width: 100%">');
		var s = (resp.posts.length == 1) ? '' : 's';
		result.push('<tr><td colspan="2" class="search_result_title">' + resp.posts.length + ' post' + s + '</td></tr>');
		for (var i in resp['posts']) {
			var post = resp['posts'][i];
			result.push(display_post(post));
		}
		result.push('</table>');
		output_posts(result.join(''));
	}
	
	// COMMENTS
	if (resp.comments.length > 0) {
		var result = [];
		result.push('<table border="1" style="border-style: solid; padding: 5px">');
		var s = (resp.comments.length == 1) ? '' : 's';
		result.push('<tr><td colspan="2" class="search_result_title">' + resp.comments.length + ' comment' + s + '</td></tr>');
		for (var i in resp['comments']) {
			var comment = resp['comments'][i];
			result.push(display_comment(comment));
		}
		result.push('</table>');
		output_comments(result.join(''));
	}

	// RELATED COMMENTS
	for (var i = resp.related.length; i > 0 && resp.related.length; i--) {
		// Remove comments that don't contain imgur albums
		if (resp.related[i].body.indexOf('imgur.com/a/') == -1) {
			resp.related.splice(i, 1);
		}
	}
	if (resp.related.length > 0) {
		var result = [];
		result.push('<table border="1" style="border-style: solid; padding: 5px">');
		var s = (resp.related.length == 1) ? '' : 's';
		result.push('<tr><td colspan="2" class="search_result_title">' + resp.related.length + ' related comment' + s + '</td></tr>');
		for (var i in resp['related']) {
			var related = resp['related'][i];
			if (related.body.indexOf('imgur.com/a/') >= 0) {
				result.push(display_comment(related));
			}
		}
		result.push('</table>');
		output_related(result.join(''));
	}
	var url = gebi('url').value.replace(/</g, '').replace(/>/g, '');
	var out = getExternalSearchLinks(url);
	output(out);
}

function display_post(post) {
	var txt;
	var url = post.url; var score = post.score; var ups = post.ups; var downs = post.downs;
	var title = post.title; var permalink = post.permalink; var created = post.created; 
	var author = post.author; var thumb = post.thumb; var subreddit = post.subreddit; 
	var comments = post.comments; var width = post.width; var height = post.height; var size = post.size;
	var imageurl = post.imageurl;
	var date = new Date(0);
	date.setUTCSeconds(created);
	txt = '<tr><td style="border-width: 0px;">';
	txt += '<table class="invisible" style="display: table; width: 100%; margin-left: auto;">';
	txt +=   '<tr>';
	txt +=     '<td class="result_arrow" style="vertical-align: bottom; padding-bottom: 3px;">';
	txt +=       '<img src="images/up.png" class="vote"></td>';
	txt +=     '<td rowspan="3" align="right">';
	txt +=       '<a href="' + url + '"><img src="' + thumb + '" class="result_thumbnail"/></a></td>';
	txt +=   '</tr><tr>'
	txt +=     '<td class="result_score"><span class="result_score">' + score + '</span></td>';
	txt +=   '</tr><tr>'
	txt +=     '<td class="result_arrow" style="vertical-align: top;"><img src="images/down.png" class="vote"></td>';
	txt +=   '</tr>';
	txt += '</table>';
	txt += '</td><td valign="top" style="border: 0px; padding-top: 0px; max-width: 600px;">';
	txt += '<table class="invisible">';
	txt +=   '<tr><td><a class="result_link" href="http://reddit.com' + permalink + '">' + title + '</a>';
	if (url.indexOf('imgur.com/a/') >= 0) {
		txt += '<span class="post_domain">&nbsp;(album - <a href="javascript:document.location.href = document.location.pathname + \'?url=cache:' + url + '\';">cached</a>)</span>';
	}
	txt += '</td></tr>';
	txt +=   '<tr><td class="result_info"><span class="result_date" style="padding-right: 5px;">';
	txt +=     '(<span class="post_ups">' + ups + '</span>|<span class="post_downs">' + downs + '</span>)</span> ';
	txt +=     ' submitted <span class="result_date" title="' + date.toUTCString() + '">' + get_time(created) + '</span>';
	txt +=     ' by <a class="post_author" href="?user=' + author + '">' + author + '</a>';
	txt +=     ' to <a class="post_author" href="http://www.reddit.com/r/' + subreddit + '">' + subreddit + '</a>';
	txt +=   '</td><tr>'
	txt +=   '<tr><td class="result_info">';
	txt +=     '<a class="result_comment_link" href="http://www.reddit.com' + permalink + '">';
	if (comments == 0) { txt += 'comment';
	} else if (comments == 1) {txt += '1 comment';
	} else { txt += comments + ' comments'; }
	txt += '</a> ';
	if (width != '' && height != '' && size != '') {
		txt += '<a class="result_image_link" href="' + imageurl + '">';
		txt += '(' + width + 'x' + height + '&nbsp;' + bytes_to_readable(size) + ')';
		txt += '</a>';
		//txt += ' <span class="post_domain">(' + width + 'x' + height + '&nbsp;' + bytes_to_readable(size) + ')</span>';
	}
	txt +=   '</td></tr>'
	txt += '</table>';
	txt +='</td></tr><tr><td style="font-size: 0.5em; visibility: hidden;">&nbsp;</td></tr>';
	return txt;
}

function display_comment(comment) {
	var txt = '';
	var score = comment.ups - comment.downs;
	var hexid = comment.hexid; var postid = comment.postid;
	var created = comment.created; var author = comment.author;
	var body = comment.body; var imageurl = comment.imageurl;
	var width = comment.width; var height = comment.height; var size = comment.size;
	var date = new Date(0);
	date.setUTCSeconds(created);
	if (comment.url != null) {
		body = markdown_to_html(body, comment.url);
	} else {
		body = markdown_to_html(body, comment.imageurl);
	}
	txt = '<tr><td valign="top" style="border-width: 0px;">';
	txt += '<table class="invisible" valign="top" style="display: table; width: 100%; vertical-align: top;">';
	txt +=   '<tr>';
	txt +=     '<td class="result_arrow" style="vertical-align: bottom; padding-bottom: 4px;"><img src="images/up.png" class="vote"></td>';
	txt +=   '</tr>'; // <tr><td style="font-size: 0.3em;">&nbsp;</td></tr><tr>';
	txt +=     '<td class="result_arrow" style="vertical-align: top;"><img src="images/down.png" class="vote"></td>';
	txt +=   '</tr>';
	txt += '</table>';
	txt += '</td><td valign="top" style="border: 0px; padding-top: 0px;">';
	txt += '<table class="invisible" style="max-width: 600px;">';
	txt +=   '<tr><td class="result_comment_info">';
	txt +=     '<a class="comment_author" href="?user=' + author + '">' + author + '</a> ';
	txt +=     score + ' point';
	if (score != 1) { txt += 's'; }
	txt +=     ' <span class="result_date" title="' + date.toUTCString() + '">' + get_time(created) + '';
	txt +=     ' (<span class="comment_ups">' + comment.ups + '</span>|<span class="comment_downs">' + comment.downs + '</span>)</span>';
	txt +=   '</td></tr>';
	txt +=   '<tr><td class="result_comment_body">';
	txt +=     body;
	txt +=   '</td><tr>'
	txt +=   '<tr><td class="result_info">';
	txt +=     '<a class="result_comment_link" href="http://reddit.com/comments/' + postid + '/_/' + hexid + '">permalink</a> ';
	if (width != 0 && height != 0 && size != 0) {
		txt += '<a class="result_image_link" href="' + imageurl + '">';
		txt += '(' + width + 'x' + height + '&nbsp;' + bytes_to_readable(size) + ')';
		txt += '</a>';
	}
	txt +=   '</td></tr>'
	txt += '</table>';
	txt +='</td></tr><tr><td style="font-size: 0.5em; visibility: hidden;">&nbsp;</td></tr>';
	return txt;
}

function markdown_to_html(text, relevant_url) {
	var h = text;
	h = h.replace(/\n /g, '\n').replace(/ \n/g, '\n').replace(/\n\n/g, '\n').replace(/\n/g, '<br>')
	var result = '';
	var i = h.indexOf("http://");
	var j; var url; var re; var previous = 0;
	while (i >= 0) {
		result += h.substring(previous, i);
		j = i + 7;
		while (j < h.length && h.charAt(j) != '\n' && h.charAt(j) != ' ' && h.charAt(j) != ')' && h.charAt(j) != '<' && h.charAt(j) != ']') {
			j++;
		}
		url = h.substring(i, j);
		if (url == relevant_url) {
			result += '<a class="relevant_url" href="' + url + '">' + url + '</a>';
		} else {
			result += '<a href="' + url + '">' + url + '</a>';
		}
		previous = j;
		i = h.indexOf("http://", previous);
	}
	result += h.substring(previous);
	return result;
}

function get_time(seconds) {
	var diff = Math.round(new Date().getTime() / 1000) - seconds;
	var d = {
		'second' : 60,
		'minute' : 60,
		'hour'   : 24,
		'day'    : 30,
		'month'  : 12,
		'year'   : 1000
	};
	for (var key in d) {
		if (diff <= d[key]) {
			diff = diff.toFixed(0);
			var result = diff + ' ';
			result += key;
			if (diff != 1)
				result += 's';
			result += ' ago';
			return result;
		}
		diff /= d[key];
	}
	return '? days ago';
}

function bytes_to_readable(bytes) {
	var scale = ['B', 'kB', 'mB'];
	for (var i = scale.length - 1; i >= 0; i--) {
		var cur = Math.pow(1024, i);
		if (cur < bytes) {
			return (bytes / cur).toFixed(1) + scale[i];
		}
	}
	return '?bytes'
}

function get_subreddits() {
	var request = makeHttpObject();
	gebi("subreddits").innerHTML = '<i>loading...</i>';
	request.open("GET", 'subreddits.cgi?get=true', true);
	request.send(null);
	request.onreadystatechange = function() {
		if (request.readyState == 4) { 
			if (request.status == 200) {
				// success
				handleGetSubredditsResponse(request.responseText);
			} else {
				// error
				gebi('subreddits').innerHTML = "<b>error: " + request.status + "</b>";
			}
		}
	}
}
function handleGetSubredditsResponse(responseText) {
	var json = JSON.parse(responseText);
	if (json['error'] != null) {
		gebi('subreddits').innerHTML = 'error: ' + error;
		return;
	}
	var subreddits = json['subreddits'];
	var output = '<div class="subreddits_header">monitoring ' + subreddits.length + ' subreddits</div><br>';
	for (var i in subreddits) {
		output += '<span class="subreddit" style="display: inline; padding-right: 15px; line-height: 200%;">';
		output += '<a class="subreddit" href="http://www.reddit.com/r/' + subreddits[i] + '" target="_new">' + subreddits[i] + '</a></span> ';
	}
	gebi('subreddits').innerHTML = output;
}

function sendStatusRequest() {
	var request = makeHttpObject();
	request.open("GET", 'status.cgi', true);
	request.send(null);
	request.onreadystatechange = function() {
		if (request.readyState == 4) { 
			if (request.status == 200) {
				// success
				handleStatusResponse(request.responseText);
			} else {
				// error
				gebi('database_status').innerHTML = "error! async request status code: " + request.status;
			}
		}
	}
}
function handleStatusResponse(responseText) {
	var resp = JSON.parse(responseText)["status"];
	gebi("db_images").innerHTML     = number_commas(resp['images']);
	gebi("db_posts").innerHTML      = number_commas(resp['posts']);
	gebi("db_comments").innerHTML   = number_commas(resp['comments']);
	gebi("db_albums").innerHTML     = number_commas(resp['albums']);
	gebi("db_subreddits").innerHTML = number_commas(resp['subreddits']);
}

// Add commas to the thousands places in a number
function number_commas(x) {
	return x.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

// Create new XML request object
function makeHttpObject() {
	try { return new XMLHttpRequest();
	} catch (error) {}
	try { return new ActiveXObject("Msxml2.XMLHTTP");
	} catch (error) {}
	try { return new ActiveXObject("Microsoft.XMLHTTP");
	} catch (error) {}
	throw new Error("Could not create HTTP request object.");
}

// Check URL to see if a query was passed and we need to search immediately
function checkURL() {
	var query = parent.document.URL;
	if (query.indexOf('?url=') >= 0) {
		var url = query.substring(query.indexOf('?url=') + 5);
		url = decodeURIComponent(url);
		url = decodeURIComponent(url);
		gebi("url").value = url;
		search_click();
		return true;
	} else if (query.indexOf('?user=') >= 0) {
		var user = query.substring(query.indexOf('?user=') + 6);
		gebi("url").value = '';
		gebi("user").value = user;
		gebi("user_row").style.display = 'table-row';
		user_click();
		return true;
	}
	return false;
}

function setTheme() {
	var theme = getCookie('theme');
	if (theme == '') 
		theme = 'dark';
	var oldlink = document.getElementsByTagName("link")[0];
 	
        var newlink = document.createElement("link")
        newlink.setAttribute("rel", "stylesheet");
        newlink.setAttribute("type", "text/css");
        newlink.setAttribute("href", theme + '.css');
	 
        document.getElementsByTagName("head")[0].replaceChild(newlink, oldlink);
}

function setCookie(key, value) {
        document.cookie = key + '=' + value + '; expires=Fri, 27 Dec 2999 00:00:00 UTC; path=/';
}
function getCookie(key) {
        var cookies = document.cookie.split('; ');
        for (var i in cookies) {
                var pair = cookies[i].split('=');
                if (pair[0] == key)
                        return pair[1];
        }
        return "";
}

function over18() {
	if (getCookie('over18') != 'true') {
		var question = '';
		question += 'This site may contain material intended for users 18 years and over.\n\n';
		question += 'Press OK if you are over the age of 18.\n\n';
		question += 'Press Cancel if you are under the age of 18 or do not wish to visit this site.';
		var answer = confirm(question);
		if (answer) {
			setCookie('over18', 'true');
		} else {
			window.location.href = 'about:blank';
		}
	}
}

function menu_database_click() {
	var menu = gebi("database_menu");
	if (menu.className == 'menuActive') {
		collapseMenu();
		return;
	}
	if (!menu.alreadyRequested) {
		sendStatusRequest();
	}
	gebi('database_dropdown').style.display  = 'table-cell';
	gebi('subreddit_dropdown').style.display = 'none';
	gebi('about_dropdown').style.display     = 'none';
	menu.className  = 'menuActive';
	gebi('subreddit_menu').className = 'menu';
	gebi('about_menu').className     = 'menu';
	// Disable further requests for updates after 1
	menu.alreadyRequested = true;
}
function menu_subreddit_click() {
	var menu = gebi("subreddit_menu");
	if (menu.className == 'menuActive') {
		collapseMenu();
		return;
	}
	if (!menu.alreadyRequested) {
		get_subreddits();
	}
	gebi('database_dropdown').style.display  = 'none';
	gebi('subreddit_dropdown').style.display = 'table-cell';
	gebi('about_dropdown').style.display     = 'none';
	gebi('database_menu').className  = 'menu';
	menu.className = 'menuActive';
	gebi('about_menu').className     = 'menu';
	// Disable further updates
	menu.alreadyRequested = true;
}
function menu_about_click() {
	if (gebi('about_menu').className == 'menuActive') {
		collapseMenu();
		return;
	}
	gebi('database_dropdown').style.display  = 'none';
	gebi('subreddit_dropdown').style.display = 'none';
	gebi('about_dropdown').style.display     = 'table-cell';
	gebi('database_menu').className  = 'menu';
	gebi('subreddit_menu').className = 'menu';
	gebi('about_menu').className     = 'menuActive';
}
function collapseMenu() {
	gebi('database_dropdown').style.display  = 'none';
	gebi('subreddit_dropdown').style.display = 'none';
	gebi('about_dropdown').style.display     = 'none';
	gebi('database_menu').className  = 'menu';
	gebi('subreddit_menu').className = 'menu';
	gebi('about_menu').className     = 'menu';
}

function gotoRoot() {
	window.location = document.location.pathname;
}

function user_redirect_check(user) {
	var re = /^([-_]?[A-Za-z0-9])*$/;
	if (!re.test(user)) { return false; }
	gebi("user").value = user;
	redirect_user();
	return true;
}

// Function to run after window has loaded
function init() {
	over18();
	setTheme();
	if (!checkURL()) {
		// Not loading an image; randomly pick a url to display
		var urls = ['http://i.imgur.com/Xz42HQa.jpg', 'http://i.imgur.com/IFdWn.jpg', 'http://i.imgur.com/3qrBM.jpg', 'http://i.minus.com/ibu7TXSVaN73Nn.gif', 'http://i.imgur.com/O1IXj.jpg', 'http://i.imgur.com/QNj8w.jpg', 'http://i.imgur.com/xA1wr.jpg', 'http://i.imgur.com/54SAK.jpg', 'http://i.imgur.com/EpMv9.jpg', 'http://i.imgur.com/9VAfG.jpg', 'http://i.imgur.com/OaSfh.gif', 'http://i.imgur.com/iHjXO.jpg', 'http://i.imgur.com/IDLu8.jpg', 'http://i.imgur.com/ReKZC.jpg', 'http://i.imgur.com/mhvSa.jpg', 'http://i.imgur.com/qfzpA.jpg'];
		gebi('url').value = urls[Math.floor(Math.random() * urls.length)];
	}
}

window.onload = init;

