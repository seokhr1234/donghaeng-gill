import {sha256} from '@noble/hashes/sha2.js';
import {utf8ToBytes,bytesToHex} from '@noble/hashes/utils.js';
export function createHash(name){if(name!=='sha256')throw Error('Unsupported digest');let text='';return {update(value){text+=value;return this},digest(){return bytesToHex(sha256(utf8ToBytes(text)))}}}
