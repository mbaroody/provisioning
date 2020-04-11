" Mappings
"
" Map Y to act like D and C, i.e. to yank until EOL, rather than act as yy,
" which is the default
map Y y$

" Map <C-L> (redraw screen) to also turn off search highlighting until the
" next search
nnoremap <C-L> :nohl<CR><C-L>

"indent shortcuts
nnoremap <space> za
vnoremap <space> zf

" nice window sitting
map \| :vsp<CR>
map - :sp<CR>

" remap esc to jj in insert mode
imap jj <Esc>

" remap buffer switching to ,
map , :bnext<CR>

" map nertree toggle
map <C-n> :NERDTreeToggle<CR>

" buffer stuff
" pressing <F5> gets you a list of buffers,
" then just type buffer number and enter
nnoremap <F5> :buffers<CR>:buffer<Space>

" remap easier buffer switching
map <C-J> :bnext<CR>
map <C-K> :bprev<CR>

" bracket and paren closing
inoremap {      {}<Left>
inoremap {<CR>  {<CR>}<Esc>O
inoremap {{     {
inoremap {}     {}

inoremap [      []<Left>
inoremap [<CR>  [<CR>]<Esc>O
inoremap [[     [
inoremap []     []

inoremap (      ()<Left>
inoremap (<CR>  (<CR>)<Esc>O
inoremap ((     (
inoremap ()     ()

inoremap "      ""<Left>
inoremap "<CR>  "<CR>"<Esc>O
inoremap ""     "
inoremap ""     ""

" highlight when searching for matching bracket (%)
noremap  % v%

" yank to  clipboard
vnoremap ytc "+y
nnoremap ytc "+y

" paste from clipboard
nnoremap pfc "+p

" go to just before the first non-blank text of the line
inoremap II <Esc>I
" move to end of line, but stay in insert mode
inoremap AA <Esc>A
" start editing on a new line above the current line
inoremap OO <Esc>O
