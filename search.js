// Set new string prototype for 'trim()'
if (typeof (String.prototype.trim) === "undefined") {
        String.prototype.trim = function() {
                return String(this).replace(/^\s+|\s+$/g, '');
        };
}

// Shortened version of getElementById
function gebi(id) { return document.getElementById(id); }

// Statusbar (overwrites previous text)
function statusbar(text) { gebi("status").innerHTML = text; }

// Output (appends text)
function output(text)          { gebi("output").innerHTML          += text + "<br>"; }
function output_posts(text)    { gebi("output_posts").innerHTML    = text; }
function output_comments(text) { gebi("output_comments").innerHTML = text; }

// Redirect to the page so the URL changes & we know what image is being searched
function redirect_search() {
	var url = gebi("url").value;
	url = url.replace(/[.]/g, '%2E');
	url = encodeURIComponent(url);
	document.location.href = 'http://i.rarchives.com/?url=' + url;
}

function search_click() {
	var url = gebi("url");
	sendSearchRequest('search.cgi?url=' + url.value);
	url.blur();
}

function redirect_user() {
	var user = gebi("user").value;
	document.location.href = 'http://i.rarchives.com/?user=' + user;
}

function user_click() {
	var user = gebi("user");
	sendSearchRequest('search.cgi?user=' + user.value);
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

// Sends asynchronous XML request, handles response
function sendSearchRequest(query) {
	var request = makeHttpObject();
	statusbar('<img src="images/spinner_dark.gif"/> searching...');
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
	if (resp.posts.length == 0 && resp.comments.length == 0) {
		// No results, show alternatives
		statusbar('<span class="search_count_empty">no results</span>');
		var url = gebi('url').value; //.replace(/</g, '').replace(/>/g, '');
		var out = '';
		out += '<ul>';
		out += '<li> <a class="external_link" href="http://images.google.com/searchbyimage?image_url=' + url + '">search on google images</a></li>';
		out += '<li> <a class="external_link" href="http://www.tineye.com/search?pluginver=bookmark_1.0&url=' + url + '">search on tineye</a></li>';
		out += '<li> <a class="external_link" href="http://www.karmadecay.com/' + url.replace(/http:\/\//, '') + '">search on karmadecay</a></li>';
		out += '</ul>';
		output(out);
		return;
	}
	statusbar('');
	
	// POSTS
	if (resp.posts.length > 0) {
		result = [];
		result.push('<table border="1" style="border-style: solid; padding: 5px">');
		var s = (resp.posts.length == 1) ? '' : 's';
		result.push('<tr><td colspan="2" class="search_result_title">' + resp.posts.length + ' post' + s + '</td></tr>');
		for (var i in resp['posts']) {
			var post = resp['posts'][i];
			result.push(display_post(post));
		}
		result.push('</table><br><br>');
		output_posts(result.join(''));
	}
	
	// COMMENTS
	if (resp.comments.length > 0) {
		result = []
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
}

function display_post(post) {
	var txt;
	var url = post.url; var score = post.score; var ups = post.ups; var downs = post.downs;
	var title = post.title; var permalink = post.permalink; var created = post.created; 
	var author = post.author; var thumb = post.thumb; var subreddit = post.subreddit; 
	var comments = post.comments; var width = post.width; height = post.height; size = post.size;
	var date = new Date(0);
	date.setUTCSeconds(created);
	txt = '<tr><td style="border-width: 0px;">';
	txt += '<table class="invisible" style="display: table; width: 100%;">';
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
	txt += '</td><td valign="top" style="border: 0px; padding-top: 0px;">';
	txt += '<table class="invisible">';
	txt +=   '<tr><td><a class="result_link" href="http://reddit.com' + permalink + '">' + title + '</a></td></tr>';
	txt +=   '<tr><td class="result_info"><span class="result_date" style="padding-right: 5px;">';
	txt +=     '(<span style="color: #ff4500; padding: 1px;"><b>' + ups + '</b></span>|<span style="color: #00f; padding: 1px;"><b>' + downs + '</b></span>)</span> ';
	txt +=     ' submitted <span class="result_date" title="' + date.toUTCString() + '">' + get_time(created) + '</span>';
	txt +=     ' by <a href="/?user=' + author + '">' + author + '</a>';
	txt +=     ' to <a href="http://www.reddit.com/r/' + subreddit + '">' + subreddit + '</a>';
	txt +=   '</td><tr>'
	txt +=   '<tr><td class="result_info">';
	txt +=     '<a class="result_comment_link" href="http://www.reddit.com' + permalink + '">' + comments + ' comments</a> ';
	if (width != '' && height != '' && size != '') {
		txt +=     width + 'x' + height + ' (' + bytes_to_readable(size) + ')';
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
	var body = comment.body;
	var width = comment.width; height = comment.height; size = comment.size;
	var date = new Date(0);
	date.setUTCSeconds(created);
	txt = '<tr><td valign="top" style="border-width: 0px;">';
	txt += '<table class="invisible" valign="top" style="display: table; width: 100%; vertical-align: top;">';
	txt +=   '<tr>';
	txt +=     '<td class="result_arrow" style="vertical-align: bottom; padding-bottom: 4px;"><img src="images/up.png" class="vote"></td>';
	txt +=   '</tr>'; // <tr><td style="font-size: 0.3em;">&nbsp;</td></tr><tr>';
	txt +=     '<td class="result_arrow" style="vertical-align: top;"><img src="images/down.png" class="vote"></td>';
	txt +=   '</tr>';
	txt += '</table>';
	txt += '</td><td valign="top" style="border: 0px; padding-top: 0px;">';
	txt += '<table class="invisible">';
	txt +=   '<tr><td class="result_comment_info">';
	txt +=     '<a style="padding-right: 5px;" href="/?user=' + author + '"><b>' + author + '</b></a> ';
	txt +=     score + ' points ';
	txt +=     '<span class="result_date" title="' + date.toUTCString() + '">' + get_time(created) + '';
	txt +=     ' (<span style="color: #ff4500; padding: 1px;"><b>' + comment.ups + '</b></span>|<span style="color: #00f; padding: 1px;"><b>' + comment.downs + '</b></span>)</span>';
	txt +=   '</td></tr>';
	txt +=   '<tr><td class="result_comment_body">';
	txt +=     markdown_to_html(body);
	txt +=   '</td><tr>'
	txt +=   '<tr><td class="result_info">';
	txt +=     '<a class="result_comment_link" href="http://reddit.com/comments/' + postid + '/_/' + hexid + '">permalink</a> ';
	txt +=     width + 'x' + height + ' (' + bytes_to_readable(size) + ')';
	txt +=   '</td></tr>'
	txt += '</table>';
	txt +='</td></tr><tr><td style="font-size: 0.5em; visibility: hidden;">&nbsp;</td></tr>';
	return txt;
}

function markdown_to_html(text) {
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
		result += '<a href="' + url + '">' + url + '</a>';
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

function add_subreddit() {
	var subreddit = gebi('subreddit').value;
	sendAddSubredditRequest('add_sub.cgi?subreddit=' + subreddit);
}

function sendAddSubredditRequest(query) {
	var request = makeHttpObject();
	gebi("subreddit_status").innerHTML = 'adding...';
	request.open("GET", query, true);
	request.send(null);
	request.onreadystatechange = function() {
		if (request.readyState == 4) { 
			if (request.status == 200) {
				// success
				handleAddSubredditResponse(request.responseText);
			} else {
				// error
				gebi('subreddit_status').innerHTML = "error! async request status code: " + request.status;
			}
		}
	}
}

function handleAddSubredditResponse(responseText) {
	//output("response from server: " + responseText);
	var resp = JSON.parse(responseText);
	gebi('subreddit_status').innerHTML = resp['result'];
}

function sendStatusRequest() {
	var request = makeHttpObject();
	gebi("db_images").innerHTML     = '...';
	gebi("db_posts").innerHTML      = '...';
	gebi("db_comments").innerHTML   = '...';
	gebi("db_albums").innerHTML     = '...';
	gebi("db_subreddits").innerHTML = '...';
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
	var oldlink = document.getElementsByTagName("link").item('dark.css');
 	
        var newlink = document.createElement("link")
        newlink.setAttribute("rel", "stylesheet");
        newlink.setAttribute("type", "text/css");
        newlink.setAttribute("href", theme + '.css');
	 
        document.getElementsByTagName("head").item(0).replaceChild(newlink, oldlink);
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

// Function to run after window has loaded
function init() {
	over18();
	//setTheme();
	//sendStatusRequest();
	if (!checkURL()) {
		// Not loading an image; randomly pick a url to display
		var urls = ['http://i.imgur.com/IFdWn.jpg', 'http://i.imgur.com/3qrBM.jpg', 'http://i.minus.com/ibu7TXSVaN73Nn.gif', 'http://i.imgur.com/O1IXj.jpg', 'http://i.imgur.com/UHdXc.jpg', 'http://i.imgur.com/QNj8w.jpg', 'http://i.imgur.com/xA1wr.jpg', 'http://i.imgur.com/54SAK.jpg', 'http://i.imgur.com/EpMv9.jpg', 'http://i.imgur.com/9VAfG.jpg', 'http://i.imgur.com/OaSfh.gif', 'http://i.imgur.com/iHjXO.jpg', 'http://i.imgur.com/IDLu8.jpg'];
		gebi('url').value = urls[Math.floor(Math.random() * urls.length)];
	}
}

window.onload = init;

