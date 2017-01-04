#!/usr/bin/env python3
# encoding: utf-8

top = '.'
out = 'build'

def options(opt):
	opt.load('LotusWaf', tooldir='.')

def configure(cfg):
	cfg.load('LotusWaf', tooldir='.')

def build(bld):
	bld.project('skeleton');
