//gotime.js
//drawing from mdn fetch api
console.log("distant, dim, orbit");

const resource = "notes/1bit_redraw.png"
async function getData(url) {
	try {
	  const response = await fetch(url);
	  if (!response.ok) {
		throw new Error(`Response status: ${response.status}`);
	  }
  
	  const json = await response.json();
	  console.log(json);
	} catch (error) {
	  console.error(error.message);
	}
  }
  