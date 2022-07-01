let mapleader = '-'

call plug#begin('~/.nvim/plugged')
Plug 'neoclide/coc.nvim', {'branch': 'release'}
Plug 'scrooloose/nerdtree'
Plug 'tpope/vim-surround'
Plug 'tpope/vim-commentary'
Plug 'tpope/vim-eunuch'
Plug 'sheerun/vim-polyglot'
Plug 'puremourning/vimspector'
Plug 'godlygeek/tabular'
Plug 'junegunn/fzf.vim'
Plug 'tpope/vim-fugitive'
Plug 'airblade/vim-gitgutter'
" Plug 'python-mode/python-mode', { 'for': 'python', 'branch': 'develop' }
" Plug 'davidhalter/jedi-vim'
Plug 'vim-airline/vim-airline'
Plug 'vim-airline/vim-airline-themes'
Plug 'EdenEast/nightfox.nvim'
call plug#end()

" coc extensions
let g:coc_global_extensions = [
  \'coc-tsserver',
  \'coc-swagger',
  \'coc-solargraph',
  \'coc-python',
  \'coc-metals',
  \'coc-json',
  \'coc-java',
  \'coc-spell-checker'
\]

"fzf
set rtp+=$HOME/.fzf/
nnoremap <leader>f :GFiles<CR>
nnoremap <leader>s :Rg<CR>
nnoremap <leader>b :Buffers<CR>
nnoremap <leader>: :History:<CR>

colorscheme terafox

"nerdtree
nnoremap <leader><C-n> :NERDTreeToggle<CR>

"python-mode"
" let g:pymode_options_colorcolumn = 0
" let g:pymode_run_bind = '<leader>R'

let g:airline#extensions#ale#enabled = 1

" ultisnips
" let g:UltiSnipsExpandTrigger='<c-k>'
" let g:UltiSnipsJumpForwardTrigger='<c-b>'
" let g:UltiSnipsJumpBackwardTrigger='<c-z>'
" let g:UltiSnipsEditSplit='vertical'
" let g:UltiSnipsSnippetDirectories=[$HOME.'/.nvim/plugged/vim-snippets/UltiSnips', $HOME.'/.config/nvim/UltiSnips_custom']

" mappings
source $HOME/.config/nvim/mappings.vim

" misc settings
source $HOME/.config/nvim/misc.vim
