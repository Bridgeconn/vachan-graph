var connectionData = null;

$(document).ready(function () {
  var localStorage =  window.localStorage;
  let loadedData =  localStorage.getItem('connectionData');

  if (!loadedData) {
  	$('#heading').html("Success");
  	$('#message').html("Loading fresh data from file!");
  	$('.toast').toast('show')
    connectionData = connection;
  } else {
  	$('#heading').html("Success");
  	$('#message').html("Loading connection saved in localStorage");
  	$('.toast').toast('show')
    connectionData = JSON.parse(loadedData);
  }


  var table1 = $("#table1").DataTable({
    data: data_set,
    select: {
        style:    'multi',
    },
    "order": [[ 4, 'asc' ], [ 0, 'asc' ]],
    columns: [
      { title: "Name" },
      { title: "ID",
        visible: false, },
      { title: "Description",
  		render: function ( data, type, row, meta ) {
	      return '<button class="popup" onClick="view(event);" type="button" data-trigger="focus" data-toggle="popover" title="'+row[0]+'" data-content="'+data.replace("/","").replace("<br>","\n")+'" data-placement="right" data-container="body">View</button> ' +data

	    }
	  },
      { title: "Source"},
      { title: "Status",
        // data: null,
        // defaultContent: '',
        visible: false,
        render: function ( data, type, row, meta ) {
          let conn = connectionData.find((a) => ( (a.factgrid && a.factgrid.includes(row[1])) || 
                (a.ubs && a.ubs.includes(row[1])) ||
                (a.wiki && a.wiki.includes(row[1])) )  );
          let cellValue = null;
          let index = -1; 
          if (!conn) {
            cellValue = 'pink';
          } else {
            if (conn.linked === 'manual') {
              cellValue = 'green'
            } else {
              cellValue = 'orange'
            }
            index = connectionData.indexOf(conn);
          }
          cellValue += " " +index.toString()
          return cellValue
        }
      }
    ],
    rowCallback: function (row, data, dataIndex) {
      let found = connectionData.find((a) => {
        return (a.factgrid && a.factgrid.includes(data[1])) || 
        		(a.ubs && a.ubs.includes(data[1])) ||
        		(a.wiki && a.wiki.includes(data[1]));
      });
      if (found === undefined) {
      	$(row).removeClass("table-danger").removeClass("table-success").removeClass("table-warning").addClass("table-danger");
      } else if (found.linked === "manual") {
      	// $(row).removeClass();
        $(row).removeClass("table-danger").removeClass("table-success").removeClass("table-warning").addClass("table-success");
      } else {
      	// $(row).removeClass();
        $(row).removeClass("table-danger").removeClass("table-success").removeClass("table-warning").addClass("table-warning");
      }
    },

    fnDrawCallback: function( oSettings ) {
	    $('[data-toggle="popover"]').popover({
		  trigger: 'focus',
		  container: 'body'
		})   
    },
    initComplete: function () {
        $('#table1 thead tr th').each( function () {
            var title = $(this).text();
            $(this).html( title+ '<input type="text" placeholder="Search" onClick="view(event);"/>' );
        } );

        // Apply the search
        this.api().columns().every( function () {
            var that = this;

            $( 'input', this.header() ).on( 'keyup change clear', function () {
                if ( that.search() !== this.value ) {
                    that
                        .search( this.value )
                        .draw();
                }
            } );
        } );
    }
  });


  var table2 = $('#table2').DataTable({
  	data: data_set,
  	columns: [
      { title: "Name" },
      { title: "ID",
        visible: false, },
      { title: "Description",
        "render": function ( data, type, row, meta ) {
        return '<button class="popup" type="button" data-trigger="focus" data-toggle="popover" title="'+row[0]+'" data-content="'+data.replace("/","").replace("<br>","\n")+'" data-placement="right" data-container="body">View</button> ' +data
        }
      },
      { title: "Source"}
  	],
  	sDom: 't',
      fnDrawCallback: function( oSettings ) {
        $('[data-toggle="popover"]').popover({
        trigger: 'focus',
        container: 'body'
      })   
    },
  });

  $('#conn_display').hide();
  $('#connectbutton').show();
  $('#disconnectbutton').hide();
  

  table1.on( 'select', function ( e, dt, type, indexes ) {
      if ( type === 'row' ) {
          var id = table1.rows( indexes ).data()[0][1];
          var source = table1.rows( indexes ).data()[0][3];
          let conn = null;
          for (let obj of connectionData) {
            if ( source === 'factgrid' && obj.factgrid && obj.factgrid.includes(id)) {
              conn = obj;
              break;
            } else if (source === 'ubs' && obj.ubs && obj.ubs.includes(id)) {
            	conn = obj;
            	break;
            } else if (source === 'wiki' && obj.wiki && obj.wiki.includes(id)) {
            	conn = obj;
            	break
            } else { }
          }
          if (conn === null) {
          	$("#connectbutton").show();
          	if($("#conn_display").is(":visible")){
	          	$("#addbutton").show();
          	}
  
          } else {
	          let ids = '('
	      	  if (conn.factgrid){
	      	  	  let f_ids = '';
	              for (let f_id of conn.factgrid) { f_ids += f_id + ")|(" }
	              ids += f_ids;
	      	  }
	          if (conn.ubs){
	            let u_ids = ''
	            for (let u_id of conn.ubs) { u_ids += u_id + ")|(" }
	            ids += u_ids;
	          }
	          if (conn.wiki) {
	            let w_ids = ''
	            for (let w_id of conn.wiki) { w_ids += w_id + ")|(" }
	            ids += w_ids
	          }
 			  $('#conn_display').show();
	          table2.search(ids.slice(0,-2),true,false).draw()
	          // $('#connectbutton').hide();
	          $('#disconnectbutton').show();
    		  $("#table1").DataTable().rows().deselect();

          }
      }
  } );

});

function view(e) {
	e.stopPropagation();
}

function addConnection() {
  if ($("#table2").DataTable().rows( { page: 'current' } ).data()){
    let rows = $("#table2").DataTable().rows( { page: 'current' } ).data();
    let id = rows[0][1]
    let src = rows[0][3]
    let item = null;
    for (let conn of connectionData) {
      if (src === 'factgrid'){
        if ("factgrid" in conn && conn['factgrid'].includes(id) ) {
          item = conn;
          break;
        }
      } else if (src === 'ubs'){
        if ("ubs" in conn && conn['ubs'].includes(id) ) {
          item = conn;
          break;
        }
      } else if (src === 'wiki'){
        if ("wiki" in conn && conn['wiki'].includes(id) ) {
          item = conn;
          break;
        }
      }
    }
    if (item) {
   	  var f_ids = [];
		  var u_ids = [];
		  var w_ids = [];
		  if ($("#table1").DataTable().rows( { selected: true, page: 'current' } ).data()){
		    let rows = $("#table1").DataTable().rows( { selected: true, page: 'current' } ).data();
		    for (let i=0; i<rows.length; i+=1) {
		     let src = rows[i][3]
		     if (src === 'factgrid') {
		      f_ids.push(rows[i][1])
		     } else if (src === 'ubs') {
		     	u_ids.push(rows[i][1])
		     } else if ( src === 'wiki') {
		     	w_ids.push(rows[i][1])
		     }
		    }
		  }
		  if (f_ids.length + u_ids.length + w_ids < 1 ) {
		  	$('#heading').html("<span style='background-color: orange'>Warning</span>");
		  	$('#message').html("Not enough items selected!");
		  	$('.toast').toast('show')
		    return;
		  }
		  var okflag = true;
		  for (let conn of connectionData) {
		    if (conn.factgrid) {
		      for (let f_id of conn.factgrid) {
		        if (f_ids.includes(f_id) ) {
		            okflag = false;
		        }
		      }
		    }
		    if (conn.ubs) {
		      for (let u_id of conn.ubs) {
		        if (u_ids.includes(u_id) ) {
		            okflag = false;
		        }
		      }
		    }
		    if (conn.wiki) {
		      for (let w_id of conn.wiki) {
		        if (w_ids.includes(w_id) ) {
		            okflag = false;
		        }
		      }
		    }
		  }
		  if (!okflag) {
		  	$('#heading').html("<span style='background-color: orange'>Warning</span>");
		  	$('#message').html("Connection already exists, for newly added item(s)!");
		  	$('.toast').toast('show')
		    return;
		  }
		  var index = connectionData.indexOf(item);
		  connectionData.splice(index, 1);
		  if (f_ids.length > 0) {
        if (!item.factgrid) {item['factgrid'] = []}
         item['factgrid'] = item['factgrid'].concat(f_ids) 
      }
      if (u_ids.length > 0) {
        if (!item.ubs) {item['ubs'] = []}
         item['ubs'] = item['ubs'].concat(u_ids) 
      }
      if (w_ids.length > 0) {
        if (!item.wiki) {item['wiki'] = []}
         item['wiki'] = item['wiki'].concat(w_ids) 
      }
		  item['linked'] = "manual";
		  connectionData.push(item);
	    	$('#heading').html("Success");
		  	$('#message').html("Added connection");
		  	$('.toast').toast('show')
		  saveConnections()
		  $("#table1").DataTable().rows().deselect();
		  $("#table1").DataTable().draw('page');

    } else {
	  	$('#heading').html("<span style='background-color: orange'>Warning</span>");
	  	$('#message').html("Connection not found");
	  	$('.toast').toast('show')
    }
  }

}


function connect() {
  var f_ids = [];
  var u_ids = [];
  var w_ids = [];
  var item = null;
  if ($("#table1").DataTable().rows( { selected: true, page: 'current' } ).data()){
    let rows = $("#table1").DataTable().rows( { selected: true, page: 'current' } ).data();
    for (let i=0; i<rows.length; i+=1) {
     let src = rows[i][3]
     if (src === 'factgrid') {
      f_ids.push(rows[i][1])
     } else if (src === 'ubs') {
     	u_ids.push(rows[i][1])
     } else if ( src === 'wiki') {
     	w_ids.push(rows[i][1])
     }
    }
  }
  if (f_ids.length + u_ids.length + w_ids < 2 ) {
  	$('#heading').html("<span style='background-color: orange'>Warning</span>");
  	$('#message').html("Not enough items selected!");
  	$('.toast').toast('show')
    return;
  }
  var okflag = true;
  for (let conn of connectionData) {
    if (conn.factgrid) {
      for (let f_id of conn.factgrid) {
        if (f_ids.includes(f_id) ) {
            okflag = false;
        }
      }
    }
    if (conn.ubs) {
      for (let u_id of conn.ubs) {
        if (u_ids.includes(u_id) ) {
            okflag = false;
        }
      }
    }
    if (conn.wiki) {
      for (let w_id of conn.wiki) {
        if (w_ids.includes(w_id) ) {
            okflag = false;
        }
      }
    }
  }
  if (!okflag) {
  	$('#heading').html("<span style='background-color: orange'>Warning</span>");
  	$('#message').html("Connection already exists, for all or some items!");
  	$('.toast').toast('show')
    return;
  }
  let obj = {};
  if (f_ids.length > 0) { obj['factgrid'] = f_ids }
  if (u_ids.length > 0) { obj['ubs'] = u_ids }
  if (w_ids.length > 0) { obj['wiki'] = w_ids }
  obj['linked'] = "manual";
  connectionData.push(obj);
  $('#heading').html("Success");
  $('#message').html("Connected");
  $('.toast').toast('show')
  saveConnections()
  $("#table1").DataTable().rows().deselect();
  $("#table1").DataTable().draw('page');
  return;
}

function disconnect() {
  var f_ids = [];
  var u_ids = []
  var w_ids = [];
  var item = null;

  if ($("#table2").DataTable().rows( { page: 'current' } ).data()){
    let rows = $("#table2").DataTable().rows( { page: 'current' } ).data();
    for (let i=0; i<rows.length; i+=1) {
     let src = rows[i][3]
     if (src === 'factgrid') {
      f_ids.push(rows[i][1])
     } else if (src === 'ubs') {
     	u_ids.push(rows[i][1])
     } else if ( src === 'wiki') {
     	w_ids.push(rows[i][1])
     }
 	}
  }
  if (f_ids.length > 0) {
    for (let conn of connectionData) {
      for (let f_id of f_ids ) {
        if ("factgrid" in conn && conn['factgrid'].includes(f_id) ) {
          item = conn;
          break;
        }
      }
    }       
  } else if (u_ids.length > 0) {
    for (let conn of connectionData) {
      for (let u_id of u_ids) {
        if ("ubs" in conn && conn['ubs'].includes(u_id)) {
          item = conn;
          break;
        }
      }
    }       

  } else if (w_ids.length > 0) {
    for (let conn of connectionData) {
      for (let w_id of w_ids) {
        if ("wiki" in conn && conn['wiki'].includes(w_id)) {
          item = conn;
          break;
        }
      }
    }       

  } else {
  	$('#heading').html("<span style='background-color: orange'>Warning</span>");
  	$('#message').html("Nothing selected for diconnecting!");
  	$('.toast').toast('show')
  }
  if (item == null) {
	  	$('#heading').html("<span style='background-color: orange'>Warning</span>");
	  	$('#message').html("Connection not found!");
	  	$('.toast').toast('show')
        return
  } 
  let okflag = true;
  if (item.factgrid) {
    for (let f_id of item.factgrid) {
      if (!f_ids.includes(f_id))
        okflag = false;
        break;
    }
  }
  if (okflag && item.ubs) {
    for (let u_id of item.ubs) {
      if (!u_ids.includes(u_id))
        okflag = false;
        break;
    }
  }
  if (okflag && item.wiki) {
    for (let w_id of item.wiki) {
      if (!w_ids.includes(w_id))
        okflag = false;
        break;
    }
  }
  if (!okflag) {
  	$('#heading').html("<span style='background-color: orange'>Warning</span>");
  	$('#message').html("Not all items connected together are selected for disconnecting!!!");
  	$('.toast').toast('show')
      return;
  }
  let i = connectionData.indexOf(item)
  connectionData.splice(i,1)
  	$('#heading').html("Success");
  	$('#message').html("Removed the selected link!");
  	$('.toast').toast('show')
  saveConnections()      
  $("#table1").DataTable().rows().deselect();
  $("#table1").DataTable().draw('page');

  $('#conn_display').hide();
  $('#connectbutton').show();

}




function saveConnections() {
  var localStorage = window.localStorage;
  localStorage.setItem('connectionData', JSON.stringify(connectionData));
}

function downloadConnections() {
  //creating an invisible element 
  var text = 'var connection = '+JSON.stringify(connectionData);
  var element = document.createElement('a'); 
  element.setAttribute('href',  
  'data:text/plain;charset=utf-8, ' 
  + encodeURIComponent(text)); 
  element.setAttribute('download', 'connected_ne.js'); 

  document.body.appendChild(element); 
  element.click(); 

  document.body.removeChild(element); 
}
