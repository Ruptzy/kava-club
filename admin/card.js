/* The standings card: 1080 x 1350, the site's own look, drawn on a canvas.
   Used by the admin page's "Share a night" and by card.html?date=YYYY-MM-DD.
   drawStandingsCard(canvas, night, opts) — opts: {leagueNight, next:[{k,v}]} */
(function(){
  var VOID='#0C0D0E', CREAM='#FFF6E8', SCARLET='#FE273A', PANEL='#151618', RULE='rgba(255,246,232,.14)', INK2='#B9B1A6', INK3='#7E776E';
  var MEDAL={1:'#E4B02F',2:'#C9CBCF',3:'#C67A3A'};
  var TYPES={league:'League night',social:'Social Sunday',study:'Study night',adobe:'Intermediate+ study night',tournament:'Tournament',special:'Club battle',lecture:'Lecture',simul:'Simul'};
  var DAYS=['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'];
  var MONTHS=['January','February','March','April','May','June','July','August','September','October','November','December'];
  var WORDS=['','ONE','TWO','THREE','FOUR','FIVE','SIX','SEVEN','EIGHT','NINE','TEN','ELEVEN','TWELVE'];

  function longDate(d){ var p=d.split('-'), dt=new Date(+p[0],+p[1]-1,+p[2]); return DAYS[dt.getDay()]+' '+dt.getDate()+' '+MONTHS[dt.getMonth()]+' '+dt.getFullYear(); }
  function ranks(rows){ var out=[],rank=0,prev=null; rows.forEach(function(r,i){ if(r.pts!==prev){rank=i+1;prev=r.pts;} out.push(rank); }); return out; }
  function pts(v){ return (typeof v==='number'&&v%1)?String(Math.floor(v))+'½':String(v); }
  function wrap(c,text,x,y,maxW,lh){ var words=String(text).split(' '),line=''; words.forEach(function(w){ var t=line?line+' '+w:w; if(c.measureText(t).width>maxW&&line){c.fillText(line,x,y);y+=lh;line=w;}else line=t; }); if(line)c.fillText(line,x,y); return y+lh; }

  window.drawStandingsCard=function(cv, n, opts){
    opts=opts||{};
    var x=cv.getContext('2d'), W=1080, H=1350, M=64;
    x.textAlign='left'; x.textBaseline='alphabetic'; x.letterSpacing='0px';
    x.fillStyle=VOID; x.fillRect(0,0,W,H);

    // a corner of chessboard fading in, and a scarlet glow: the subject, not decoration
    var g=x.createRadialGradient(W,H,40,W,H,520); g.addColorStop(0,'rgba(255,246,232,.09)'); g.addColorStop(1,'rgba(255,246,232,0)');
    var sq=46; for(var i=0;i<14;i++) for(var j=0;j<14;j++){ if((i+j)%2) continue; x.fillStyle=g; x.fillRect(W-(i+1)*sq,H-(j+1)*sq,sq,sq); }
    var g2=x.createRadialGradient(0,0,10,0,0,520); g2.addColorStop(0,'rgba(254,39,58,.22)'); g2.addColorStop(1,'rgba(254,39,58,0)');
    x.fillStyle=g2; x.fillRect(0,0,700,700);
    x.fillStyle=CREAM; x.fillRect(0,0,W,6);

    var type=(TYPES[n.type]||'Club night');
    var isLeague=n.type==='league' && (n.standings||[]).length;
    var label=['KAVA SOCIAL CHESS CLUB', 'NIGHT '+(opts.no||n.no||'')];
    if(n.season) label.push('SEASON '+n.season);
    x.fillStyle=SCARLET; x.font='700 19px "JetBrains Mono"'; x.letterSpacing='4px';
    x.fillText(label.join('  ·  '), M, M+18);

    // title
    x.fillStyle=CREAM; x.letterSpacing='-1px'; x.font='900 118px Archivo'; x.fontStretch='semi-expanded';
    var t1, t2;
    if(isLeague && opts.leagueNight){ t1='NIGHT '+(WORDS[opts.leagueNight]||opts.leagueNight); t2='STANDINGS'; }
    else if(isLeague){ t1='LEAGUE'; t2='STANDINGS'; }
    else { t1=type.toUpperCase().split(' ')[0]; t2=type.toUpperCase().split(' ').slice(1).join(' ')||'NIGHT'; }
    if(x.measureText(t1).width>W-2*M) x.font='900 96px Archivo';
    x.fillText(t1, M, M+140); x.fillText(t2, M, M+250);
    x.fontStretch='normal';

    var meta=[longDate(n.date).toUpperCase()]; if(n.played) meta.push(n.played+' PLAYERS'); if(n.rounds) meta.push(n.rounds+' ROUNDS');
    x.fillStyle=INK2; x.font='400 20px "JetBrains Mono"'; x.letterSpacing='2px'; x.fillText(meta.join('  ·  '), M, M+300);

    var top=M+350, st=n.standings||[];
    if(!st.length){
      // no scoreboard: the title and the line, large
      x.fillStyle=CREAM; x.font='900 60px Archivo'; x.letterSpacing='-0.5px'; x.fontStretch='semi-expanded';
      var yy=wrap(x,(n.title||type).toUpperCase(),M,top+50,W-2*M,66); x.fontStretch='normal';
      if(n.line){ x.fillStyle=INK2; x.font='italic 300 36px Newsreader'; x.letterSpacing='0px'; wrap(x,'“'+n.line+'”',M,yy+40,W-2*M,46); }
    } else {
      var colW=(W-2*M-44)/2, colX=[M, M+colW+44], rowH=56, headH=44;
      function bracket(b, cx, cy){
        x.fillStyle=SCARLET; x.font='700 17px "JetBrains Mono"'; x.letterSpacing='3px'; x.textAlign='left';
        x.fillText(String(b.bracket||'').toUpperCase(), cx, cy+14);
        x.fillStyle=RULE; x.fillRect(cx, cy+26, colW, 1);
        var y=cy+headH, rk=ranks(b.rows);
        b.rows.forEach(function(r,i){
          var cyc=y+rowH/2, m=MEDAL[rk[i]];
          x.beginPath(); x.arc(cx+17,cyc,17,0,Math.PI*2);
          if(m){ x.fillStyle=m; x.fill(); x.fillStyle=VOID; } else { x.strokeStyle=RULE; x.lineWidth=1.5; x.stroke(); x.fillStyle=INK3; }
          x.font='700 15px "JetBrains Mono"'; x.letterSpacing='0px'; x.textAlign='center'; x.fillText(String(rk[i]),cx+17,cyc+5); x.textAlign='left';
          x.fillStyle=CREAM; x.font='800 30px Archivo';
          var name=r.name+(r.note?'  ('+r.note+')':''); if(x.measureText(name).width>colW-190) x.font='800 24px Archivo';
          x.fillText(name, cx+52, cyc+10);
          x.fillStyle=INK3; x.font='400 16px "JetBrains Mono"'; x.letterSpacing='1px'; x.textAlign='right'; x.fillText(r.rec||'', cx+colW, cyc+6);
          x.fillStyle=CREAM; x.font='900 32px Archivo'; x.fontStretch='semi-expanded'; x.letterSpacing='0px'; x.fillText(pts(r.pts), cx+colW-96, cyc+11); x.fontStretch='normal'; x.textAlign='left';
          x.fillStyle=RULE; x.fillRect(cx, y+rowH-1, colW, 1);
          y+=rowH;
        });
        return y;
      }
      // brackets: the tallest ones share the columns evenly
      var order=st.slice(), left=[], right=[], hl=0, hr=0;
      order.forEach(function(b){ var h=headH+b.rows.length*rowH+36; if(hl<=hr){left.push(b);hl+=h;}else{right.push(b);hr+=h;} });
      var yA=top, yB=top;
      left.forEach(function(b){ yA=bracket(b,colX[0],yA)+36; });
      right.forEach(function(b){ yB=bracket(b,colX[1],yB)+36; });

      // the panel goes under the shorter column: upsets if there are any, the line, what's next
      var px=(yA<=yB)?colX[0]:colX[1], py=Math.min(yA,yB), ph=H-M-py-70;
      if(ph>150){
        x.fillStyle=PANEL; x.fillRect(px,py,colW,ph); x.fillStyle=SCARLET; x.fillRect(px,py,3,ph);
        var uy=py+38;
        if(n.upsets&&n.upsets.length){
          x.fillStyle=SCARLET; x.font='700 17px "JetBrains Mono"'; x.letterSpacing='3px'; x.fillText('UPSETS',px+26,uy); uy+=44;
          n.upsets.forEach(function(u){
            x.fillStyle=CREAM; x.font='italic 300 27px Newsreader'; x.letterSpacing='0px'; x.fillText(u[0]+' over '+u[1],px+26,uy);
            x.fillStyle=SCARLET; x.font='700 16px "JetBrains Mono"'; x.textAlign='right'; x.fillText(u[2]||'',px+colW-22,uy-1); x.textAlign='left';
            uy+=36;
          });
          uy+=8;
        }
        if(n.line && !(n.upsets&&n.upsets.length) && uy+80<py+ph){ x.fillStyle=INK2; x.font='italic 300 24px Newsreader'; x.letterSpacing='0px'; uy=wrap(x,'“'+n.line+'”',px+26,uy+8,colW-48,32)+6; }
        (opts.next||[]).forEach(function(nx){
          if(uy+62>py+ph) return;
          x.fillStyle=SCARLET; x.font='700 15px "JetBrains Mono"'; x.letterSpacing='3px'; x.fillText(nx.k.toUpperCase(),px+26,uy+20);
          x.fillStyle=CREAM; x.letterSpacing='0px'; var fs=24; x.font='800 '+fs+'px Archivo';
          while(x.measureText(nx.v).width>colW-52 && fs>16){ fs-=1; x.font='800 '+fs+'px Archivo'; }
          x.fillText(nx.v,px+26,uy+50);
          uy+=66;
        });
      }
    }

    x.fillStyle=RULE; x.fillRect(M,H-M-30,W-2*M,1);
    x.fillStyle=INK3; x.font='400 17px "JetBrains Mono"'; x.letterSpacing='2px'; x.textAlign='left';
    x.fillText('KAVASOCIALCHESSCLUB.COM/NIGHTS/',M,H-M+2);
    x.textAlign='right'; x.fillText('IN-HOUSE RATINGS  ·  SUNDAYS & TUESDAYS 8PM',W-M,H-M+2); x.textAlign='left';
    x.letterSpacing='0px';
  };

  // helpers the callers share
  window.cardHelpers={
    leagueNightNumber:function(nights,n){ if(n.type!=='league'||!n.season) return 0; return nights.filter(function(o){return o.type==='league'&&o.season===n.season&&o.date<=n.date;}).length; },
    nextUp:function(dateStr,events){
      var p=dateStr.split('-'), d=new Date(+p[0],+p[1]-1,+p[2]), out=[];
      var A=new Date(2026,7,30);
      var t=new Date(d); for(var i=1;i<=21;i++){ t.setDate(t.getDate()+1); if(t.getDay()===0 && (Math.floor(Math.round((t-A)/864e5)/7)%2)===0){ out.push({k:'Next league night',v:DAYS[t.getDay()].slice(0,3)+' '+t.getDate()+' '+MONTHS[t.getMonth()].slice(0,3)+' · 8PM'}); break; } }
      var ev=(events||[]).filter(function(e){return e.date&&e.date>dateStr;}).sort(function(a,b){return a.date<b.date?-1:1;})[0];
      if(ev){ var q=ev.date.split('-'), ed=new Date(+q[0],+q[1]-1,+q[2]); if((ed-d)/864e5<=30) out.unshift({k:'Coming up',v:String(ev.title||'').split(':')[0]+' · '+DAYS[ed.getDay()].slice(0,3)+' '+ed.getDate()+' '+MONTHS[ed.getMonth()].slice(0,3)}); }
      return out;
    }
  };
})();
